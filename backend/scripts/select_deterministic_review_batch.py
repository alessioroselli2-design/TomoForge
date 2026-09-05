from __future__ import annotations

from typing import Any, Iterable


def _nonempty_json(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list, tuple, set, str)):
        return len(value) > 0
    return True


def is_deterministic_review_candidate(record: dict[str, Any]) -> bool:
    """Return True only for records that can be AI-reviewed without interpretation.

    This gate is deliberately conservative. It does not change review_status and is
    intended to preserve the human review gate while identifying records whose
    structured fields are exact copies of their source fields and whose provenance
    is already complete.
    """
    if record.get("review_status") != "needs_review":
        return False
    if record.get("ai_review_status") == "verified":
        return False
    if record.get("source_language") != "it":
        return False
    if record.get("translation_status") != "not_required":
        return False
    if not record.get("source_key") or not _nonempty_json(record.get("source_refs")):
        return False
    if _nonempty_json(record.get("review_flags")):
        return False

    exact_pairs = (
        ("name", "source_name"),
        ("normalized_name", "source_normalized_name"),
        ("description", "source_description"),
        ("full_text", "source_full_text"),
        ("attributes", "source_attributes"),
    )
    return all(record.get(current) == record.get(source) for current, source in exact_pairs)


def select_deterministic_review_batch(
    records: Iterable[dict[str, Any]], *, limit: int = 5
) -> list[dict[str, Any]]:
    """Select a stable, bounded batch without modifying any record."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    candidates = [record for record in records if is_deterministic_review_candidate(record)]
    candidates.sort(key=lambda record: str(record.get("id") or ""))
    return candidates[:limit]
