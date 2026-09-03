"""Bounded recovery worker for failed reference translations.

This worker never re-reads source PDFs and never mutates immutable source
snapshots. It only delegates eligible failed records to the existing
single-record retry path, which already owns leasing and provider fallback.
"""
from __future__ import annotations

from typing import Any

from core.config import TRANSLATION_PROCESSING_STATUS
from services.library import retry_private_reference_translation
from services.record_paging import list_collection_rows
from services.reference_translation import translation_required


RETRYABLE_TRANSLATION_ERRORS = frozenset({
    "provider_rate_limited",
    "provider_rate_limited_exhausted",
    "provider_translation_failed",
    "provider_translation_incomplete",
    "provider_translation_invalid",
})


async def list_owner_reference_records(
    user_id: str,
    *,
    db,
    page_size: int = 1000,
) -> list[dict]:
    """Read the complete owner corpus without a silent single-request cutoff."""
    return await list_collection_rows(
        db.private_reference_records,
        {"user_id": user_id},
        page_size=page_size,
    )


def _is_retry_candidate(record: dict) -> bool:
    return (
        record.get("review_status") != "verified"
        and translation_required(record.get("source_language"))
        and record.get("translation_status") == "failed"
        and str(record.get("translation_error") or "") in RETRYABLE_TRANSLATION_ERRORS
    )


def summarize_translation_retry(records: list[dict], user_id: str) -> dict[str, Any]:
    """Return owner-scoped translation recovery status without writes."""
    translatable = [
        record
        for record in records
        if (
            record.get("review_status") != "verified"
            and translation_required(record.get("source_language"))
        )
    ]
    failed = [record for record in translatable if record.get("translation_status") == "failed"]
    processing = [
        record
        for record in translatable
        if record.get("translation_status") == TRANSLATION_PROCESSING_STATUS
    ]
    pending = [
        record
        for record in translatable
        if record.get("translation_status")
        not in {"translated", "failed", TRANSLATION_PROCESSING_STATUS}
    ]
    translated = [
        record for record in translatable if record.get("translation_status") == "translated"
    ]
    retryable = [record for record in failed if _is_retry_candidate(record)]
    errors: dict[str, int] = {}
    for record in failed:
        error = str(record.get("translation_error") or "unknown")
        errors[error] = errors.get(error, 0) + 1
    not_ready = len(failed) + len(processing) + len(pending)
    return {
        "owner_user_id": user_id,
        "translatable_total": len(translatable),
        "translated_total": len(translated),
        "failed_total": len(failed),
        "processing_total": len(processing),
        "pending_total": len(pending),
        "translation_not_ready": not_ready,
        "retryable_total": len(retryable),
        "blocked_total": len(failed) - len(retryable),
        "errors": dict(sorted(errors.items())),
        "ready_for_verification": not_ready == 0,
    }


async def translation_retry_status(user_id: str, *, db) -> dict[str, Any]:
    records = await list_owner_reference_records(user_id, db=db)
    return summarize_translation_retry(records, user_id)


async def run_translation_retries(
    user_id: str,
    *,
    db,
    batch_size: int = 5,
) -> dict[str, Any]:
    """Retry at most ``batch_size`` failed translations through the safe lease path."""
    records = await list_owner_reference_records(user_id, db=db)
    pending = sorted(
        (record for record in records if _is_retry_candidate(record)),
        key=lambda record: str(record.get("id", "")),
    )

    processed = 0
    recovered = 0
    still_failed = 0
    for record in pending[:batch_size]:
        result = await retry_private_reference_translation(
            user_id,
            record["id"],
            db=db,
        )
        processed += 1
        if result.get("translation_status") == "translated":
            recovered += 1
        elif result.get("translation_status") == "failed":
            still_failed += 1

    result = await translation_retry_status(user_id, db=db)
    result["processed_records"] = processed
    result["recovered_records"] = recovered
    result["still_failed_records"] = still_failed
    return result
