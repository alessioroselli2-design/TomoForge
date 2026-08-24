import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable, Callable, Optional

from fastapi import HTTPException

from core.config import (
    MANUAL_PRELOAD_LEASE_SECONDS,
    MANUAL_PRELOAD_MAX_ATTEMPTS,
    MANUAL_PRELOAD_PAGE_BATCH_SIZE,
    TRANSLATION_RATE_LIMIT_RETRY_DELAYS,
    utc_now,
)
from core.db import db as _singleton_db
from schemas.library import ManualPreloadInput, ReferenceImportInput

logger = logging.getLogger("tomeforge")

MANUAL_PRELOAD_ACTIVE_WORKERS: set[str] = set()
_RATE_LIMIT_DRAIN_PAGE_SIZE = 200


def manual_preload_summary(job: Optional[dict], page_count: Optional[int]) -> dict:
    """Return progress metadata that is safe to show in the browser."""
    if not job:
        return {
            "status": "not_started",
            "current_page": 1,
            "page_count": page_count,
            "percent": 0,
            "records_imported": 0,
            "records_updated": 0,
            "records_flagged": 0,
            "records_skipped": 0,
            "pages_needing_ocr": [],
            "last_error": "",
            "translation_processing_confirmed": False,
            "external_processing_confirmed": False,
            "translation_retry_at": None,
            "translation_retry_attempt": 0,
        }
    total = page_count or job.get("page_count") or 0
    current_page = max(1, int(job.get("current_page") or 1))
    completed_pages = min(total, max(0, current_page - 1)) if total else 0
    return {
        "status": job.get("status", "queued"),
        "current_page": current_page,
        "page_count": total or None,
        "percent": round((completed_pages / total) * 100) if total else 0,
        "records_imported": int(job.get("records_imported") or 0),
        "records_updated": int(job.get("records_updated") or 0),
        "records_flagged": int(job.get("records_flagged") or 0),
        "records_skipped": int(job.get("records_skipped") or 0),
        "pages_needing_ocr": list(job.get("pages_needing_ocr") or []),
        "last_error": job.get("last_error") or "",
        "translation_processing_confirmed": bool(job.get("translation_processing_confirmed")),
        "external_processing_confirmed": bool(job.get("external_processing_confirmed")),
        "translation_retry_at": job.get("translation_retry_at") or None,
        "translation_retry_attempt": int(job.get("translation_retry_attempt") or 0),
    }


async def ensure_manual_preload_jobs(user_id: str, body: ManualPreloadInput, *, db=None) -> list[dict]:
    """Reconcile all supplied manuals with one durable, owner-scoped queue."""
    _db = db if db is not None else _singleton_db
    from services.library import (
        available_reference_manuals, manual_page_count,
        discard_private_manual_source_records,
        manual_requires_ocr, manual_source_duplicate_of, manual_source_fingerprint,
        manual_source_language, private_manual_import_jobs,
    )
    manuals = available_reference_manuals()
    if body.filename and body.filename not in manuals:
        raise HTTPException(status_code=400, detail="Il manuale richiesto non è disponibile localmente")
    selected_manuals = (
        {body.filename: manuals[body.filename]}
        if body.filename
        else manuals
    )

    collection = getattr(_db, "private_manual_import_jobs", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Coda di indicizzazione non disponibile: applica prima la migrazione SQL")
    existing_by_filename = {
        job.get("filename"): job
        for job in await private_manual_import_jobs(user_id, db=_db)
        if job.get("filename")
    }
    for filename, path in selected_manuals.items():
        existing = existing_by_filename.get(filename)
        source_language = manual_source_language(filename)
        translation_confirmed = True
        ocr_confirmed = True

        fingerprint = manual_source_fingerprint(path)
        duplicate_of = manual_source_duplicate_of(filename, manuals)
        changed_source = bool(existing and existing.get("source_fingerprint") != fingerprint)
        status = existing.get("status") if existing else "queued"
        if duplicate_of:
            status = "failed"
        elif changed_source or (body.filename == filename and (body.enable_translation or body.enable_ocr or body.retry)):
            status = "queued"
        page_count = manual_page_count(path)
        payload = {
            "user_id": user_id,
            "filename": filename,
            "source_language": source_language,
            "source_fingerprint": fingerprint,
            "page_count": page_count or 0,
            "translation_processing_confirmed": translation_confirmed,
            "external_processing_confirmed": ocr_confirmed,
            "status": status,
            "updated_at": utc_now(),
        }
        if existing:
            if duplicate_of:
                payload.update({
                    "last_error": f"manual_source_duplicate:{duplicate_of}",
                    "current_page": 1,
                    "attempt_count": 0,
                    "pages_needing_ocr": [],
                    "records_imported": 0,
                    "records_updated": 0,
                    "records_flagged": 0,
                    "records_skipped": 0,
                    "lease_id": "",
                    "lease_expires_at": 0,
                    "completed_at": None,
                })
            elif changed_source:
                payload.update({
                    "current_page": 1,
                    "attempt_count": 0,
                    "last_error": "",
                    "pages_needing_ocr": [],
                    "records_imported": 0,
                    "records_updated": 0,
                    "records_flagged": 0,
                    "records_skipped": 0,
                })
            elif status == "queued":
                payload.update({"lease_id": "", "lease_expires_at": 0, "last_error": ""})
            await collection.update_one({"id": existing["id"], "user_id": user_id}, {"$set": payload})
        else:
            await collection.insert_one({
                "id": f"manual_job_{uuid.uuid4().hex}",
                **payload,
                "current_page": 1,
                "attempt_count": 0,
                "last_error": f"manual_source_duplicate:{duplicate_of}" if duplicate_of else "",
                "pages_needing_ocr": [],
                "records_imported": 0,
                "records_updated": 0,
                "records_flagged": 0,
                "records_skipped": 0,
                "lease_id": "",
                "lease_expires_at": 0,
                "created_at": utc_now(),
                "completed_at": None,
            })
        if duplicate_of:
            discarded = await discard_private_manual_source_records(user_id, filename, db=_db)
            if discarded:
                logger.warning(
                    "Discarded %s records from invalid manual source %s",
                    discarded,
                    filename,
                )
    return await private_manual_import_jobs(user_id, db=_db)


async def claim_next_manual_preload_job(user_id: str, *, db=None) -> Optional[dict]:
    """Lease exactly one queued chunk so concurrent requests cannot duplicate it."""
    _db = db if db is not None else _singleton_db
    from services.library import private_manual_import_jobs
    collection = getattr(_db, "private_manual_import_jobs", None)
    if collection is None:
        return None
    now = int(time.time())
    candidates = sorted(
        (
            job for job in await private_manual_import_jobs(user_id, db=_db)
            if job.get("status") == "queued"
            or (job.get("status") == "processing" and int(job.get("lease_expires_at") or 0) < now)
        ),
        key=lambda job: (job.get("updated_at") or "", job.get("filename") or ""),
    )
    for candidate in candidates:
        lease_id = uuid.uuid4().hex
        claimed = await collection.update_one(
            {
                "id": candidate["id"],
                "user_id": user_id,
                "$or": [
                    {"status": "queued"},
                    {"status": "processing", "lease_expires_at": {"$lt": now}},
                ],
            },
            {"$set": {
                "status": "processing",
                "lease_id": lease_id,
                "lease_expires_at": now + MANUAL_PRELOAD_LEASE_SECONDS,
                "updated_at": utc_now(),
            }},
        )
        if claimed.matched_count:
            return await collection.find_one({"id": candidate["id"], "user_id": user_id})
    return None


async def renew_manual_preload_lease(
    user_id: str,
    job_id: str,
    lease_id: str,
    *,
    db=None,
    ownership_lost: Optional[asyncio.Event] = None,
) -> None:
    """Keep a long-running extraction owned until its current chunk checkpoints."""
    _db = db if db is not None else _singleton_db
    collection = getattr(_db, "private_manual_import_jobs", None)
    if collection is None:
        return
    try:
        while True:
            await asyncio.sleep(max(1, MANUAL_PRELOAD_LEASE_SECONDS // 3))
            try:
                renewed = await collection.update_one(
                    {"id": job_id, "user_id": user_id, "status": "processing", "lease_id": lease_id},
                    {"$set": {
                        "lease_expires_at": int(time.time()) + MANUAL_PRELOAD_LEASE_SECONDS,
                        "updated_at": utc_now(),
                    }},
                )
            except Exception:
                logger.exception("Could not renew the automatic manual preload lease")
                continue
            if not renewed.matched_count:
                if ownership_lost is not None:
                    ownership_lost.set()
                return
    except asyncio.CancelledError:
        raise


async def _drain_rate_limited_ids(records_collection: Any, query: dict) -> list[str]:
    """Return IDs of all records matching *query*, paginating to avoid fixed caps."""
    ids: list[str] = []
    offset = 0
    while True:
        page = await records_collection.find(query).sort("id", 1).to_list(
            _RATE_LIMIT_DRAIN_PAGE_SIZE, offset
        )
        ids.extend(r["id"] for r in page)
        if len(page) < _RATE_LIMIT_DRAIN_PAGE_SIZE:
            break
        offset += _RATE_LIMIT_DRAIN_PAGE_SIZE
    return ids


async def _retry_rate_limited_translations(
    user_id: str,
    source_filename: str,
    records_collection: Any,
    delays: tuple[int, ...] = TRANSLATION_RATE_LIMIT_RETRY_DELAYS,
    job_updater: Optional[Callable[[int, str], Awaitable[None]]] = None,
    *,
    db=None,
) -> int:
    """Retry rate-limited records from *source_filename* with exponential back-off."""
    _db = db if db is not None else _singleton_db
    from services.library import retry_private_reference_translation
    rate_limit_query = {
        "user_id": user_id,
        "source_key": source_filename,
        "translation_error": "provider_rate_limited",
    }
    for attempt, delay in enumerate(delays):
        retry_at = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
        if job_updater is not None:
            await job_updater(attempt, retry_at)
        logger.info(
            "Traduzione con rate-limit: attesa %ss prima del tentativo %s/%s per %s",
            delay, attempt + 1, len(delays), source_filename,
        )
        await asyncio.sleep(delay)

        pending_ids = await _drain_rate_limited_ids(records_collection, rate_limit_query)
        if not pending_ids:
            return 0

        for record_id in pending_ids:
            try:
                await retry_private_reference_translation(user_id, record_id, db=_db)
            except Exception as exc:
                logger.warning("Retry rate-limit per %s fallito: %s", record_id, exc)

        remaining_ids = await _drain_rate_limited_ids(records_collection, rate_limit_query)
        if not remaining_ids:
            return 0

    still_limited_ids = await _drain_rate_limited_ids(records_collection, rate_limit_query)
    for record_id in still_limited_ids:
        record = await records_collection.find_one({"id": record_id, "user_id": user_id})
        if not record:
            continue
        if record.get("review_status") == "verified":
            continue
        new_flags = sorted(set(record.get("review_flags") or []) | {"traduzione_da_verificare"})
        await records_collection.update_one(
            {
                "id": record_id,
                "user_id": user_id,
                "translation_error": "provider_rate_limited",
                "review_status": {"$ne": "verified"},
            },
            {"$set": {
                "review_flags": new_flags,
                "review_status": "needs_review",
                "translation_error": "provider_rate_limited_exhausted",
                "updated_at": utc_now(),
            }},
        )
    return len(still_limited_ids)


async def process_manual_preload_job(user_id: str, job: dict, *, db=None) -> None:
    """Process one bounded page chunk and checkpoint the durable queue."""
    _db = db if db is not None else _singleton_db
    from services.library import (
        available_reference_manuals, manual_page_count, manual_requires_ocr,
        discard_private_manual_source_records,
        manual_source_duplicate_of,
        import_private_reference_manuals,
    )
    collection = getattr(_db, "private_manual_import_jobs", None)
    if collection is None:
        return
    lease_id = job.get("lease_id")
    if not lease_id:
        return
    owned_query = {
        "id": job["id"],
        "user_id": user_id,
        "status": "processing",
        "lease_id": lease_id,
    }
    filename = job["filename"]
    manuals = available_reference_manuals()
    path = manuals.get(filename)
    if not path:
        await collection.update_one(
            owned_query,
            {"$set": {"status": "failed", "last_error": "manual_source_missing", "lease_id": "", "lease_expires_at": 0, "updated_at": utc_now()}},
        )
        return
    duplicate_of = manual_source_duplicate_of(filename, manuals)
    if duplicate_of:
        discarded = await discard_private_manual_source_records(user_id, filename, db=_db)
        await collection.update_one(
            owned_query,
            {"$set": {
                "status": "failed",
                "last_error": f"manual_source_duplicate:{duplicate_of}",
                "current_page": 1,
                "attempt_count": 0,
                "pages_needing_ocr": [],
                "records_imported": 0,
                "records_updated": 0,
                "records_flagged": 0,
                "records_skipped": 0,
                "lease_id": "",
                "lease_expires_at": 0,
                "completed_at": None,
                "updated_at": utc_now(),
            }},
        )
        logger.error(
            "Manual preload stopped for %s because its bytes duplicate %s; discarded %s invalid records",
            filename,
            duplicate_of,
            discarded,
        )
        return
    page_count = manual_page_count(path)
    if not page_count:
        await collection.update_one(
            owned_query,
            {"$set": {"status": "failed", "last_error": "manual_page_count_unavailable", "lease_id": "", "lease_expires_at": 0, "updated_at": utc_now()}},
        )
        return
    current_page = max(1, int(job.get("current_page") or 1))
    if current_page > page_count:
        await collection.update_one(
            owned_query,
            {"$set": {"status": "completed", "page_count": page_count, "completed_at": utc_now(), "lease_id": "", "lease_expires_at": 0, "updated_at": utc_now()}},
        )
        return

    end_page = min(page_count, current_page + MANUAL_PRELOAD_PAGE_BATCH_SIZE - 1)
    ownership_lost = asyncio.Event()
    renewal_task = asyncio.create_task(
        renew_manual_preload_lease(
            user_id,
            job["id"],
            lease_id,
            db=_db,
            ownership_lost=ownership_lost,
        )
    )

    async def _stop_renewal() -> bool:
        renewal_task.cancel()
        await asyncio.gather(renewal_task, return_exceptions=True)
        return ownership_lost.is_set()

    try:
        report = await import_private_reference_manuals(
            user_id,
            ReferenceImportInput(
                filenames=[filename],
                start_page=current_page,
                end_page=end_page,
                use_ai_ocr=manual_requires_ocr(filename),
                external_processing_confirmed=bool(job.get("external_processing_confirmed")),
                translation_processing_confirmed=bool(job.get("translation_processing_confirmed")),
                auto_accept=True,
            ),
            db=_db,
        )
    except Exception as exc:
        if await _stop_renewal():
            return False
        attempts = int(job.get("attempt_count") or 0) + 1
        retry_status = "queued" if attempts < MANUAL_PRELOAD_MAX_ATTEMPTS else "failed"
        checkpoint = await collection.update_one(
            owned_query,
            {"$set": {
                "status": retry_status,
                "attempt_count": attempts,
                "last_error": str(exc)[:500],
                "lease_id": "",
                "lease_expires_at": 0,
                "updated_at": utc_now(),
            }},
        )
        if not checkpoint.matched_count:
            return False
        logger.warning("Manual preload failed for %s page %s: %s", filename, current_page, exc)
        return
    if await _stop_renewal():
        return False

    source_report = next((source for source in report.sources if source.get("filename") == filename), {})

    translation_rate_limited = int(source_report.get("translation_rate_limited") or 0)
    records_collection = getattr(_db, "private_reference_records", None)
    if translation_rate_limited and records_collection is not None:
        marked_rate_limited = await collection.update_one(
            owned_query,
            {"$set": {"last_error": "translation_rate_limited", "updated_at": utc_now()}},
        )
        if not marked_rate_limited.matched_count:
            return False
        rate_limit_renewal = asyncio.create_task(
            renew_manual_preload_lease(
                user_id,
                job["id"],
                lease_id,
                db=_db,
                ownership_lost=ownership_lost,
            )
        )

        async def _update_retry_state(attempt: int, retry_at: str) -> None:
            if ownership_lost.is_set():
                return
            await collection.update_one(
                owned_query,
                {"$set": {
                    "translation_retry_at": retry_at,
                    "translation_retry_attempt": attempt + 1,
                    "updated_at": utc_now(),
                }},
            )

        try:
            await _retry_rate_limited_translations(
                user_id, filename, records_collection, job_updater=_update_retry_state, db=_db
            )
        finally:
            rate_limit_renewal.cancel()
            await asyncio.gather(rate_limit_renewal, return_exceptions=True)
        if ownership_lost.is_set():
            return False

    current_pages = set(range(current_page, end_page + 1))
    unreadable_pages = sorted(
        (set(job.get("pages_needing_ocr") or []) - current_pages)
        | set(source_report.get("pages_needing_ocr") or [])
    )
    attempts = int(job.get("attempt_count") or 0)
    if source_report.get("pages_needing_ocr") and manual_requires_ocr(filename):
        next_page = current_page
        attempts += 1
        next_status = "queued" if attempts < MANUAL_PRELOAD_MAX_ATTEMPTS else "failed"
        error = "ocr_pages_unavailable"
    else:
        next_page = end_page + 1
        next_status = "completed" if next_page > page_count else "queued"
        error = ""
        attempts = 0
    checkpoint = await collection.update_one(
        owned_query,
        {"$set": {
            "status": next_status,
            "current_page": next_page,
            "page_count": page_count,
            "attempt_count": attempts,
            "last_error": error,
            "pages_needing_ocr": unreadable_pages,
            "records_imported": int(job.get("records_imported") or 0) + report.imported,
            "records_updated": int(job.get("records_updated") or 0) + report.updated,
            "records_flagged": int(job.get("records_flagged") or 0) + report.flagged_for_review,
            "records_skipped": int(job.get("records_skipped") or 0) + report.skipped,
            "lease_id": "",
            "lease_expires_at": 0,
            "translation_retry_at": None,
            "translation_retry_attempt": 0,
            "completed_at": utc_now() if next_status == "completed" else None,
            "updated_at": utc_now(),
        }},
    )
    if not checkpoint.matched_count:
        return False


async def run_manual_preload_worker(user_id: str, *, db=None) -> None:
    """Drain an owner's queue outside the HTTP request, one checkpoint at a time."""
    try:
        while True:
            job = await claim_next_manual_preload_job(user_id, db=db)
            if not job:
                return
            if await process_manual_preload_job(user_id, job, db=db) is False:
                return
    finally:
        MANUAL_PRELOAD_ACTIVE_WORKERS.discard(user_id)


def start_manual_preload_worker(user_id: str, *, db=None) -> None:
    if user_id in MANUAL_PRELOAD_ACTIVE_WORKERS:
        return
    MANUAL_PRELOAD_ACTIVE_WORKERS.add(user_id)
    asyncio.create_task(run_manual_preload_worker(user_id, db=db))


async def resume_manual_preload_workers(*, db=None) -> None:
    """Recover queued work and completed parser revisions after a restart."""
    _db = db if db is not None else _singleton_db
    from services.library import (
        available_reference_manuals, manual_page_count, manual_source_duplicate_of,
        discard_private_manual_source_records,
        manual_source_fingerprint,
    )
    collection = getattr(_db, "private_manual_import_jobs", None)
    if collection is None:
        return
    try:
        jobs = await collection.find({}).to_list(2000)
    except Exception as exc:
        if "private_manual_import_jobs" in str(exc):
            logger.warning("Automatic manual preload schema is not available yet")
            return
        raise
    owners: set[str] = set()
    manuals = available_reference_manuals()
    for job in jobs:
        if job.get("status") == "waiting_translation_consent":
            recovered = await collection.update_one(
                {
                    "id": job["id"],
                    "user_id": job.get("user_id"),
                    "status": "waiting_translation_consent",
                },
                {"$set": {
                    "status": "queued",
                    "lease_id": "",
                    "lease_expires_at": 0,
                    "last_error": "",
                    "translation_retry_at": None,
                    "translation_retry_attempt": 0,
                    "updated_at": utc_now(),
                }},
            )
            if recovered.matched_count:
                owners.add(job.get("user_id", ""))
            continue
        filename = job.get("filename")
        path = manuals.get(filename)
        duplicate_of = manual_source_duplicate_of(filename, manuals) if path else None
        if duplicate_of:
            discarded = await discard_private_manual_source_records(
                job.get("user_id", ""),
                filename,
                db=_db,
            )
            invalidated = await collection.update_one(
                {"id": job["id"], "user_id": job.get("user_id")},
                {"$set": {
                    "status": "failed",
                    "last_error": f"manual_source_duplicate:{duplicate_of}",
                    "current_page": 1,
                    "attempt_count": 0,
                    "pages_needing_ocr": [],
                    "records_imported": 0,
                    "records_updated": 0,
                    "records_flagged": 0,
                    "records_skipped": 0,
                    "lease_id": "",
                    "lease_expires_at": 0,
                    "completed_at": None,
                    "updated_at": utc_now(),
                }},
            )
            if invalidated.matched_count:
                logger.error(
                    "Manual preload stopped for %s because its bytes duplicate %s; discarded %s invalid records",
                    filename,
                    duplicate_of,
                    discarded,
                )
            continue
        if (
            job.get("status") in {"completed", "failed"}
            and path
            and job.get("source_fingerprint") != manual_source_fingerprint(path)
        ):
            reset = await collection.update_one(
                {
                    "id": job["id"],
                    "user_id": job.get("user_id"),
                    "status": {"$in": ["completed", "failed"]},
                },
                {"$set": {
                    "status": "queued",
                    "source_fingerprint": manual_source_fingerprint(path),
                    "page_count": manual_page_count(path) or 0,
                    "current_page": 1,
                    "attempt_count": 0,
                    "last_error": "",
                    "pages_needing_ocr": [],
                    "records_imported": 0,
                    "records_updated": 0,
                    "records_flagged": 0,
                    "records_skipped": 0,
                    "lease_id": "",
                    "lease_expires_at": 0,
                    "completed_at": None,
                    "updated_at": utc_now(),
                }},
            )
            if reset.matched_count:
                owners.add(job.get("user_id", ""))
            continue
        if (
            job.get("status") == "processing"
            and int(job.get("lease_expires_at") or 0) < int(time.time())
        ):
            await collection.update_one(
                {
                    "id": job["id"],
                    "status": "processing",
                    "lease_expires_at": {"$lt": int(time.time())},
                },
                {"$set": {"status": "queued", "lease_id": "", "lease_expires_at": 0, "updated_at": utc_now()}},
            )
            owners.add(job.get("user_id", ""))
        elif job.get("status") == "queued":
            owners.add(job.get("user_id", ""))
    for owner_id in owners - {""}:
        start_manual_preload_worker(owner_id, db=db)
