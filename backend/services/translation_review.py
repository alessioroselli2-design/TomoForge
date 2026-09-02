"""Bounded persistence worker for AI translation-fidelity verdicts.

The translation itself remains an immutable-source localization concern. This
worker only compares an already translated record with its stored source
snapshot and persists a separate verdict that can be invalidated by the
translation-verification fingerprint.
"""
from __future__ import annotations

from typing import Any

from services.translation_verification import (
    TRANSLATION_AI_VERIFIED,
    TRANSLATION_CONFLICT,
    TRANSLATION_FAILED,
    TRANSLATION_LOW_CONFIDENCE,
    translation_verification_is_current,
    verify_translation,
)

CURRENT_REVIEW_STATES = frozenset({
    TRANSLATION_AI_VERIFIED,
    TRANSLATION_CONFLICT,
    TRANSLATION_LOW_CONFIDENCE,
})


def _needs_translation_review(record: dict) -> bool:
    if record.get("translation_status") != "translated":
        return False
    status = str(record.get("translation_review_status") or "pending")
    return status not in CURRENT_REVIEW_STATES or not translation_verification_is_current(record)


async def translation_review_status(user_id: str, *, db) -> dict[str, Any]:
    records = await db.private_reference_records.find({"user_id": user_id}).to_list(8000)
    translated = [record for record in records if record.get("translation_status") == "translated"]
    counts = {
        "ai_verified": 0,
        "conflict": 0,
        "low_confidence": 0,
        "failed": 0,
        "pending": 0,
        "stale": 0,
    }
    for record in translated:
        status = str(record.get("translation_review_status") or "pending")
        current = translation_verification_is_current(record)
        if status in CURRENT_REVIEW_STATES and not current:
            counts["stale"] += 1
            counts["pending"] += 1
        elif status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1
    return {
        "owner_user_id": user_id,
        "translated_total": len(translated),
        "pending": counts["pending"],
        "ai_verified": counts["ai_verified"],
        "conflict": counts["conflict"],
        "low_confidence": counts["low_confidence"],
        "failed": counts["failed"],
        "stale": counts["stale"],
        "ready_for_canonicalization": counts["pending"] == 0 and counts["failed"] == 0,
    }


async def run_translation_reviews(
    user_id: str,
    *,
    db,
    batch_size: int = 5,
    comparator=None,
) -> dict[str, Any]:
    """Verify at most ``batch_size`` translated records and persist the verdict.

    Provider failures remain retryable on the next bounded run. Conflict and
    low-confidence verdicts are stable until the source/translation fingerprint
    changes; they are never silently promoted to verified.
    """
    records = await db.private_reference_records.find({"user_id": user_id}).to_list(8000)
    pending = sorted(
        (record for record in records if _needs_translation_review(record)),
        key=lambda record: str(record.get("id", "")),
    )
    processed = 0
    for record in pending[:batch_size]:
        verdict = await verify_translation(record, comparator=comparator)
        await db.private_reference_records.update_one(
            {"id": record["id"], "user_id": user_id},
            {"$set": {
                "translation_review_status": verdict["status"],
                "translation_review_confidence": verdict["confidence"],
                "translation_review_model": verdict["model"],
                "translation_reviewed_at": verdict["reviewed_at"],
                "translation_review_notes": verdict["notes"],
                "translation_review_conflict_fields": verdict["conflict_fields"],
                "translation_review_fingerprint": verdict["fingerprint"],
            }},
        )
        processed += 1

    result = await translation_review_status(user_id, db=db)
    result["processed_records"] = processed
    result["retryable_failures"] = result["failed"]
    return result
