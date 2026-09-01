import uuid
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from reference_library import (
    REFERENCE_TYPES,
    compact_text,
    normalize_reference_name,
    reference_is_trusted,
    reference_review_state,
    reference_to_card_payload,
)

from core.auth import get_current_user, require_premium
from core.db import get_db, SupabaseDatabase
from schemas.library import (
    ManualPreloadInput, ReferenceImportInput, ReferenceImportResult, ReferenceReviewInput,
)
from schemas.users import User
import services.library as _lib_svc
from services.library import (
    import_private_reference_manuals,
    manual_coverage_report,
    manual_import_progress,
    manual_source_language,
    manual_source_metadata,
    private_manual_import_jobs,
    private_reference_records,
    reference_review_details,
    reference_summary,
    retry_private_reference_translation,
)
from services.preload import (
    ensure_manual_preload_jobs,
    manual_preload_summary,
    start_manual_preload_worker,
)
from core.config import utc_now

router = APIRouter()
logger = logging.getLogger("tomeforge")


@router.get("/library/manuals")
async def private_library_manuals(user: User = Depends(require_premium), db: SupabaseDatabase = Depends(get_db)):
    """Return local import metadata only, never the manual files or page text."""
    records = await private_reference_records(user.user_id, db=db)
    jobs_by_filename = {
        job.get("filename"): job
        for job in await private_manual_import_jobs(user.user_id, db=db)
        if job.get("filename")
    }
    manuals = []
    for filename, path in _lib_svc.available_reference_manuals().items():
        source_records = [
            record for record in records
            if any(ref.get("filename") == filename for ref in record.get("source_refs", []))
        ]
        page_count = _lib_svc.manual_page_count(path)
        progress = manual_import_progress(filename, records, page_count)
        manuals.append({
            "filename": filename,
            "title": manual_source_metadata(filename)["title"],
            "source_language": manual_source_language(filename),
            "native_text": manual_source_metadata(filename)["native_text"],
            "page_count": page_count,
            "imported_records": len(source_records),
            "requires_ocr": _lib_svc.manual_requires_ocr(filename),
            "job": manual_preload_summary(jobs_by_filename.get(filename), page_count),
            **progress,
        })
    return {"manuals": manuals}


@router.post("/library/preload")
async def start_private_library_preload(
    body: ManualPreloadInput = ManualPreloadInput(),
    user: User = Depends(require_premium),
    db: SupabaseDatabase = Depends(get_db),
):
    """Start or resume automatic indexing without exposing or uploading PDFs."""
    try:
        await ensure_manual_preload_jobs(user.user_id, body, db=db)
        start_manual_preload_worker(user.user_id, db=db)
        return await private_library_manuals(user, db=db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Automatic manual preload could not be started")
        raise HTTPException(status_code=502, detail="Impossibile avviare l'indicizzazione automatica") from exc


@router.get("/library/coverage")
async def private_library_coverage(user: User = Depends(require_premium), db: SupabaseDatabase = Depends(get_db)):
    """Report record readiness by supplied manual and applicable category."""
    records = await private_reference_records(user.user_id, db=db)
    manuals = manual_coverage_report(records)
    translation_pending = sum(
        1 for record in records
        if record.get("translation_status") == "failed"
        and record.get("translation_error") in {"provider_rate_limited", "provider_rate_limited_exhausted"}
        and not reference_is_trusted(record)
    )
    totals = {
        "valid": sum(category["valid"] for manual in manuals for category in manual["categories"]),
        "to_review": sum(category["to_review"] for manual in manuals for category in manual["categories"]),
        "missing": sum(category["missing"] for manual in manuals for category in manual["categories"]),
        "translation_pending": translation_pending,
    }
    return {"manuals": manuals, "totals": totals}


@router.get("/library")
async def search_private_library(
    q: str = Query("", max_length=120),
    types: str = Query("", max_length=200),
    parent_class: str = Query("", max_length=120),
    parent_subclass: str = Query("", max_length=160),
    level: str = Query("", max_length=12),
    review_only: bool = False,
    include_unverified: bool = False,
    source_filename: str = Query("", max_length=300),
    limit: Annotated[int, Query(ge=1, le=8000)] = 40,
    user: User = Depends(get_current_user),
    db: SupabaseDatabase = Depends(get_db),
):
    from reference_library import search_reference_records
    source_filename = source_filename if isinstance(source_filename, str) else ""
    parent_class = parent_class if isinstance(parent_class, str) else ""
    parent_subclass = parent_subclass if isinstance(parent_subclass, str) else ""
    level = level if isinstance(level, str) else ""
    requested_types = {value.strip() for value in types.split(",") if value.strip()}
    if requested_types - set(REFERENCE_TYPES):
        raise HTTPException(status_code=400, detail="Tipo di contenuto non valido")
    if source_filename and source_filename not in _lib_svc.available_reference_manuals():
        raise HTTPException(status_code=400, detail="Manuale non disponibile nella biblioteca privata")
    records = await private_reference_records(user.user_id, db=db)
    if requested_types:
        records = [record for record in records if record.get("reference_type") in requested_types]
    if source_filename:
        records = [
            record for record in records
            if any(ref.get("filename") == source_filename for ref in record.get("source_refs", []))
        ]
    if review_only:
        records = [record for record in records if reference_review_state(record) == "review"]
    records = search_reference_records(
        records,
        q,
        parent_class=parent_class,
        parent_subclass=parent_subclass,
        level=level,
        limit=limit,
    )
    excluded_unverified = sum(not reference_is_trusted(record) for record in records)
    if not include_unverified:
        records = [record for record in records if reference_is_trusted(record)]
    summaries = [reference_summary(record) for record in records]
    if summaries:
        return {
            "status": "sourced",
            "records": summaries,
            "excluded_unverified": excluded_unverified,
        }
    return {
        "status": "unavailable",
        "records": [],
        "excluded_unverified": excluded_unverified,
        "message": "Il contenuto richiesto non è disponibile come fonte verificata nella tua biblioteca.",
    }


@router.post("/library/import", response_model=ReferenceImportResult)
async def import_private_library(body: ReferenceImportInput, user: User = Depends(require_premium), db: SupabaseDatabase = Depends(get_db)):
    """Per-account, resumable import. OCR is explicit because it calls OpenAI."""
    try:
        return await import_private_reference_manuals(user.user_id, body, db=db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Private manual import failed")
        raise HTTPException(status_code=502, detail="Importazione della biblioteca privata non riuscita") from exc


@router.get("/library/{reference_id}")
async def get_private_reference(reference_id: str, user: User = Depends(get_current_user), db: SupabaseDatabase = Depends(get_db)):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    return reference_summary(record)


@router.get("/library/{reference_id}/review")
async def get_private_reference_review(
    reference_id: str,
    user: User = Depends(require_premium),
    db: SupabaseDatabase = Depends(get_db),
):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    return await reference_review_details(record, db=db)


@router.post("/library/{reference_id}/apply")
async def apply_private_reference(reference_id: str, user: User = Depends(get_current_user), db: SupabaseDatabase = Depends(get_db)):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    if not reference_is_trusted(record):
        raise HTTPException(
            status_code=409,
            detail="Questo contenuto è da verificare e non può essere usato come dato certo.",
        )
    return {**reference_to_card_payload(record), "reference_id": record["id"]}


@router.post("/library/{reference_id}/translation-retry")
async def retry_private_reference_translation_endpoint(
    reference_id: str,
    user: User = Depends(require_premium),
    db: SupabaseDatabase = Depends(get_db),
):
    return reference_summary(await retry_private_reference_translation(user.user_id, reference_id, db=db))


@router.patch("/library/{reference_id}/review")
async def review_private_reference(
    reference_id: str,
    body: ReferenceReviewInput,
    user: User = Depends(require_premium),
    db: SupabaseDatabase = Depends(get_db),
):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    review_notes = body.review_notes.strip()
    update_fields: dict = {
        "review_status": body.review_status,
        "review_notes": review_notes,
        "updated_at": utc_now(),
    }
    corrections: dict = {}
    requested_name = body.name if body.name is not None else body.corrected_name
    requested_description = body.description if body.description is not None else body.corrected_description
    requested_full_text = body.full_text if body.full_text is not None else body.corrected_full_text
    requested_attributes = body.attributes if body.attributes is not None else body.corrected_attributes
    if requested_name is not None:
        name = requested_name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Il nome del contenuto non può essere vuoto")
        update_fields["name"] = name
        update_fields["normalized_name"] = normalize_reference_name(name)
        corrections["name"] = name
    if requested_description is not None:
        update_fields["description"] = compact_text(requested_description, maximum=12000)
        corrections["description"] = update_fields["description"]
    if requested_full_text is not None:
        update_fields["full_text"] = requested_full_text.strip()
        corrections["full_text"] = update_fields["full_text"]
    if requested_attributes is not None:
        update_fields["attributes"] = requested_attributes
        corrections["attributes"] = requested_attributes
    if corrections or body.review_status == "verified":
        update_fields["review_corrections"] = corrections
    if (
        not corrections
        and body.review_status == "verified"
        and (record.get("ai_review_corrections") or {}).get("canonical_invalidated") is True
    ):
        # A reviewer may first save a correction as needs_review and confirm it
        # in a second action. It becomes human-trusted without reviving the
        # stale canonical selection or provenance.
        update_fields["ai_review_corrections"] = {"canonical_invalidated": True}
    if corrections:
        # A changed canonical input must never inherit an earlier AI decision.
        # Keep legacy pending imports usable, but explicitly mark reviewed
        # canonical records as invalidated until the next bounded admin batch.
        ai_invalidation = {
            "canonical_invalidated": True,
        }
        if body.review_status != "verified":
            ai_invalidation["selected"] = False
        update_fields.update({
            "canonical_id": None,
            "ai_review_status": "pending",
            "ai_confidence": 0,
            "ai_review_model": "",
            "ai_reviewed_at": None,
            "ai_review_notes": "canonical_source_changed_by_review",
            "ai_review_corrections": ai_invalidation,
        })

    effective_name = update_fields.get("name", record.get("name", "")).strip()
    effective_full_text = update_fields.get("full_text", record.get("full_text", "")).strip()
    if body.review_status == "verified" and (not effective_name or not effective_full_text):
        raise HTTPException(
            status_code=422,
            detail="Per verificare il contenuto servono un nome e un testo completo corretti",
        )
    review_entry = {
        "id": f"review_{uuid.uuid4().hex}",
        "reference_id": record["id"],
        "user_id": user.user_id,
        "reviewer_id": user.user_id,
        "reviewer_name": user.name,
        "reviewer_email": user.email,
        "reviewed_at": utc_now(),
        "review_status": body.review_status,
        "review_notes": review_notes,
    }
    history_collection = getattr(db, "private_reference_review_history", None)
    if history_collection is None:
        raise HTTPException(status_code=503, detail="Cronologia revisioni non disponibile: applica prima la migrazione SQL")
    try:
        await history_collection.insert_one(review_entry)
    except Exception as exc:
        if "private_reference_review_history" in str(exc):
            raise HTTPException(
                status_code=503,
                detail="Cronologia revisioni non disponibile: applica prima la migrazione SQL",
            ) from exc
        raise
    try:
        if body.review_status == "verified":
            update_fields["translation_error"] = ""
        result = await db.private_reference_records.update_one(
            {"id": reference_id, "user_id": user.user_id},
            {"$set": update_fields},
        )
        if getattr(result, "matched_count", 0) != 1:
            raise RuntimeError("Il record non è più disponibile per la revisione")
    except Exception:
        # Keep the append-only trail consistent if the state update could not
        # be applied. The service role owns both rows and can compensate safely.
        await history_collection.delete_one({
            "id": review_entry["id"],
            "reference_id": reference_id,
            "user_id": user.user_id,
        })
        raise
    updated = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    fallback = {**record, **update_fields}
    return {"ok": True, **await reference_review_details(updated or fallback, db=db)}
