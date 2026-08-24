"""
TomeForge API – Entry point.

This file creates the FastAPI app, registers all routers, and retains the
compatibility symbols still used by backend tests. Route handlers use FastAPI's
``Depends()`` system for db and provider dependencies so tests can pass fakes
directly as kwargs.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os

import requests  # noqa: F401 – exposed as server.requests for test patching
import stripe  # noqa: F401 – exposed as server.stripe for test patching
from fastapi import FastAPI, HTTPException  # noqa: F401
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Core layer
# ---------------------------------------------------------------------------
from core.config import (  # noqa: F401
    ARTWORK_CLEANUP_MODEL,
    MANUAL_PRELOAD_MAX_ATTEMPTS,
    utc_now,
)
from core.db import (  # noqa: F401
    MemoryCollection,
    UpdateResult,
)
from core.auth import (  # noqa: F401
    get_current_user,
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
)
from schemas.users import (  # noqa: F401
    RegisterInput,
    SupabaseSessionInput,
    User,
)

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
from services.cards import (  # noqa: F401
    reference_snapshot_for_card,
)

from services.library import (  # noqa: F401
    gemini_ocr_manual_page,
    import_private_reference_manuals,
    manual_coverage_report,
    manual_import_progress,
    manual_requires_ocr,
    manual_source_fingerprint,
    retry_private_reference_translation,
    translate_spanish_reference_batch,
)
from services.media import (  # noqa: F401
    cleanup_artwork,
    save_artwork,
    save_file,
)
from services.payments import (  # noqa: F401
    revoke_subscription_entitlement,
    sync_subscription_entitlement,
)
from services.preload import (  # noqa: F401
    _retry_rate_limited_translations,
    claim_next_manual_preload_job,
    ensure_manual_preload_jobs,
    manual_preload_summary,
    process_manual_preload_job,
    resume_manual_preload_workers,
    run_manual_preload_worker,
)

# ---------------------------------------------------------------------------
# Router endpoint functions (for direct test calls: asyncio.run(server.fn…))
# ---------------------------------------------------------------------------
from routers.auth import (  # noqa: F401
    google_start,
    register,
    seed_mock_data,
    supabase_session,
)
from routers.cards import (  # noqa: F401
    card_history,
    card_reference_updates,
    complete_card_from_manuals,
    create_card,
    create_linked_cards,
    delete_card,
    get_card,
    redo_card_change,
    refresh_card_reference_updates,
    undo_card_change,
    update_card,
)
from routers.library import (  # noqa: F401
    apply_private_reference,
    get_private_reference_review,
    private_library_coverage,
    review_private_reference,
    search_private_library,
)
from routers.spells import (  # noqa: F401
    apply_private_spell,
)
from routers.ai import generate_content, generate_image  # noqa: F401
from routers.public import public_get_card  # noqa: F401


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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Run startup recovery while keeping the app compatible with FastAPI updates."""
    from core.config import MOCK_DATA

    if MOCK_DATA:
        await seed_mock_data()
    await resume_manual_preload_workers()
    yield


app = FastAPI(title="TomeForge API", version="1.0.0", lifespan=lifespan)

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
