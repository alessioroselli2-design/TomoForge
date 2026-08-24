"""
TomeForge API – Entry point.

This file creates the FastAPI app, registers all routers, and re-exports every
public symbol used in backend tests so ``import server; server.X`` keeps
working.  Route handlers use FastAPI's ``Depends()`` system for db and
provider dependencies so tests can pass fakes directly as kwargs.
"""
from __future__ import annotations

import os

import requests  # noqa: F401 – exposed as server.requests for test patching
import stripe  # noqa: F401 – exposed as server.stripe for test patching
from fastapi import FastAPI, HTTPException  # noqa: F401
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Core layer
# ---------------------------------------------------------------------------
from core.config import (  # noqa: F401
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    ARTWORK_CLEANUP_ENABLED,
    ARTWORK_CLEANUP_MODEL,
    GEMINI_API_KEY,
    GEMINI_TEXT_MODEL,
    JWT_SECRET,
    MANUAL_COVERAGE_CATEGORIES,
    MANUAL_PRELOAD_MAX_ATTEMPTS,
    MIME_TYPES,
    MOCK_DATA,
    MOCK_USER_EMAIL,
    MOCK_USER_PASSWORD,
    OPENAI_API_KEY,
    SEGMIND_API_KEY,
    SEGMIND_IMAGE_MODEL,
    PREMIUM_LOOKUP_KEY,
    STRIPE_WEBHOOK_SECRET,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    configuration_status,
    require_jwt_secret,
    utc_now,
)
from core.db import (  # noqa: F401
    MOCK_OBJECTS,
    MemoryCollection,
    SupabaseCursor,
    SupabaseDatabase,
    UpdateResult,
    db,
    get_db,
    get_object,
    put_object,
    supabase_auth_client,
)
from core.auth import (  # noqa: F401
    compute_premium,
    create_jwt,
    get_current_user,
    hash_password,
    is_configured_admin_email,
    require_admin,
    require_premium,
    verify_password,
)
from core.providers import (  # noqa: F401
    require_gemini,
    require_openai,
    require_segmind,
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
from schemas.ai import GenerateContentInput, GenerateImageInput  # noqa: F401
from schemas.cards import (  # noqa: F401
    Card,
    CardAppearance,
    CardBack,
    CardCreate,
    CardUpdate,
    CardVersionInput,
    LinkedCardInput,
    ManualCompletionInput,
    ReferenceUpdateInput,
)
from schemas.library import (  # noqa: F401
    ManualPreloadInput,
    ReferenceImportInput,
    ReferenceImportResult,
    ReferenceReviewInput,
    SpellImportResult,
)
from schemas.payments import CheckoutRequest, PremiumToggle  # noqa: F401
from schemas.users import (  # noqa: F401
    LoginInput,
    RegisterInput,
    SupabaseSessionInput,
    User,
)

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
from services.ai import LANGUAGES, TYPE_LABELS, TYPE_SCHEMAS, parse_ai_json  # noqa: F401
from services.cards import (  # noqa: F401
    CARD_HISTORY_FIELDS,
    CARD_HISTORY_LIMIT,
    append_card_history,
    apply_history_entry,
    card_change_patch,
    character_default_fields,
    character_manual_defaults,
    insert_cards_atomically,
    manual_completion_preview_for_card,
    merge_source_refs,
    reference_records_by_id,
    reference_snapshot_for_card,
    reference_snapshots_for_card,
    reference_update_report,
    refresh_derived_attributes,
    remove_unlinked_reference_attributes,
    resolve_reference_provenance,
    resolve_spell_provenance,
    rule_sources_for_card,
    save_card_versioned,
)
from reference_library import extract_reference_records  # noqa: F401 — test-patchable

from services.library import (  # noqa: F401
    _json_from_model_text,
    _openai_text_from_response,
    _openai_translation_response,
    available_reference_manuals,
    card_response,
    find_private_reference,
    gemini_ocr_manual_page,
    import_private_reference_manuals,
    manual_coverage_report,
    manual_import_progress,
    manual_page_count,
    manual_requires_ocr,
    manual_source_fingerprint,
    manual_source_language,
    manual_source_metadata,
    private_manual_import_jobs,
    private_reference_records,
    private_reference_review_history,
    public_card_payload,
    public_reference_snapshot,
    public_reference_update,
    reference_review_details,
    reference_summary,
    retry_private_reference_translation,
    translate_spanish_reference_batch,
)
from services.media import (  # noqa: F401
    ARTWORK_CLEANUP_PROMPT,
    cleanup_artwork,
    require_artwork_cleanup,
    save_artwork,
    save_file,
)
from services.payments import (  # noqa: F401
    premium_until_from_subscription,
    require_stripe,
    revoke_subscription_entitlement,
    stripe_field,
    sync_subscription_entitlement,
)
from services.preload import (  # noqa: F401
    MANUAL_PRELOAD_ACTIVE_WORKERS,
    _retry_rate_limited_translations,
    claim_next_manual_preload_job,
    ensure_manual_preload_jobs,
    manual_preload_summary,
    process_manual_preload_job,
    renew_manual_preload_lease,
    resume_manual_preload_workers,
    run_manual_preload_worker,
    start_manual_preload_worker,
)
from services.spells import (  # noqa: F401
    find_private_spell,
    import_private_spell_pdfs,
    private_spell_records,
    spell_summary,
)

# ---------------------------------------------------------------------------
# Router endpoint functions (for direct test calls: asyncio.run(server.fn…))
# ---------------------------------------------------------------------------
from routers.auth import (  # noqa: F401
    auth_me,
    google_start,
    health,
    login,
    logout,
    register,
    seed_mock_data,
    supabase_session,
)
from routers.cards import (  # noqa: F401
    card_history,
    card_manual_completion_preview,
    card_reference_updates,
    complete_card_from_manuals,
    create_card,
    create_linked_cards,
    delete_card,
    get_card,
    list_cards,
    redo_card_change,
    refresh_card_reference_updates,
    undo_card_change,
    update_card,
)
from routers.library import (  # noqa: F401
    apply_private_reference,
    get_private_reference,
    get_private_reference_review,
    import_private_library,
    private_library_coverage,
    private_library_manuals,
    retry_private_reference_translation_endpoint,
    review_private_reference,
    search_private_library,
    start_private_library_preload,
)
from routers.spells import (  # noqa: F401
    apply_private_spell,
    get_private_spell,
    import_private_spells,
    search_private_spells,
)
from routers.ai import generate_content, generate_image  # noqa: F401
from routers.media import download, upload  # noqa: F401
from routers.public import public_download, public_get_card  # noqa: F401
from routers.admin import admin_list_users, admin_set_premium  # noqa: F401
from routers.payments import (  # noqa: F401
    create_checkout,
    payment_status,
    root,
    stripe_webhook,
)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
import routers.auth as _auth_router
import routers.cards as _cards_router
import routers.library as _library_router
import routers.spells as _spells_router
import routers.ai as _ai_router
import routers.media as _media_router
import routers.public as _public_router
import routers.admin as _admin_router
import routers.payments as _payments_router

app = FastAPI(title="TomeForge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000"
        ).split(",")
    ],
    allow_origin_regex=r"https://.*\.replit\.dev",
    allow_methods=["*"],
    allow_headers=["*"],
)

_API = "/api"
app.include_router(_auth_router.router, prefix=_API)
app.include_router(_cards_router.router, prefix=_API)
app.include_router(_library_router.router, prefix=_API)
app.include_router(_spells_router.router, prefix=_API)
app.include_router(_ai_router.router, prefix=_API)
app.include_router(_media_router.router, prefix=_API)
app.include_router(_public_router.router, prefix=_API)
app.include_router(_admin_router.router, prefix=_API)
app.include_router(_payments_router.router, prefix=_API)


@app.on_event("startup")
async def startup() -> None:
    from core.config import MOCK_DATA
    from services.preload import resume_manual_preload_workers
    if MOCK_DATA:
        await seed_mock_data()
    await resume_manual_preload_workers()


# ---------------------------------------------------------------------------
# Production static-file serving (React build)
# ---------------------------------------------------------------------------
# When the frontend has been pre-built (production), FastAPI serves it on the
# same port so that same-origin /api/* requests reach the backend directly.
# This block is a no-op in development, where the CRA dev server handles the
# frontend and proxies /api/* to port 5001.
from pathlib import Path as _Path
from fastapi.staticfiles import StaticFiles as _StaticFiles
from fastapi.responses import FileResponse as _FileResponse

_FRONTEND_BUILD = _Path(__file__).parent.parent / "frontend" / "build"

if _FRONTEND_BUILD.is_dir():
    # /static/* – compiled JS/CSS bundles generated by craco build.
    app.mount(
        "/static",
        _StaticFiles(directory=_FRONTEND_BUILD / "static"),
        name="react-static",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _serve_spa(full_path: str) -> _FileResponse:
        """SPA catch-all: serve a build-dir file or index.html for React routes.

        Security guards:
        - /api/* paths that fell through (no matching route) get a proper 404
          rather than the SPA HTML, preserving API error semantics.
        - The resolved candidate path is checked to be inside _FRONTEND_BUILD
          before serving, preventing path-traversal / directory-escape attacks.
        """
        # Preserve 404 semantics for unmatched /api/* requests.
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Resolve the candidate and assert it stays inside the build directory.
        build_root = _FRONTEND_BUILD.resolve()
        try:
            candidate = (build_root / full_path).resolve()
            candidate.relative_to(build_root)  # raises ValueError if outside
        except (ValueError, OSError):
            # Path escapes the build dir (traversal attempt) – serve SPA root.
            return _FileResponse(build_root / "index.html")

        if candidate.is_file():
            return _FileResponse(candidate)
        return _FileResponse(build_root / "index.html")
