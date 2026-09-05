from __future__ import annotations

from typing import Any, Iterable

from scripts.select_deterministic_review_batch import select_deterministic_review_batch

MODEL = "deterministic-source-match-v1"
NOTE = (
    "Exact structured/source match; provenance present; no review flags; "
    "no translation required. Human review gate preserved."
)


def build_update_plan(
    records: Iterable[dict[str, Any]], *, limit: int = 5
) -> list[dict[str, Any]]:
    """Build a bounded update plan without mutating records or review_status.

    The returned payload is intentionally limited to AI-review metadata. It never
    changes review_status, canonical_id, source provenance, translations, or source
    content. Database writes are deliberately left to a separately verified step.
    """
    batch = select_deterministic_review_batch(records, limit=limit)
    return [
        {
            "id": record["id"],
            "ai_review_status": "verified",
            "ai_confidence": 1.0,
            "ai_review_model": MODEL,
            "ai_review_notes": NOTE,
            "ai_review_corrections": {},
        }
        for record in batch
    ]
