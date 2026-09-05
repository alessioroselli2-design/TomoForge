from __future__ import annotations

from typing import Any, Iterable


def _nonempty_json(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list, tuple, set, str)):
        return len(value) > 0
    return True


def _has_unbalanced_delimiters(value: str) -> bool:
    pairs = {')': '(', ']': '[', '}': '{'}
    openings = set(pairs.values())
    stack: list[str] = []
    for char in value:
        if char in openings:
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return True
    return bool(stack)


def _has_excessive_isolated_letters(value: str) -> bool:
    tokens = [token.strip(".,;:!?()[]{}'\"") for token in value.split()]
    alpha_tokens = [token for token in tokens if token.isalpha()]
    if len(alpha_tokens) < 4:
        return False
    isolated = sum(len(token) == 1 for token in alpha_tokens)
    return isolated >= 4 and isolated / len(alpha_tokens) >= 0.4


def _has_suspicious_name_shape(value: Any) -> bool:
    """Reject names that require interpretation before deterministic AI review.

    The automatic path is intentionally conservative. Digits, unbalanced
    delimiters, and heavily fragmented single-letter text are common extraction
    artefacts. Legitimate edge cases can still proceed through human review.
    """
    if not isinstance(value, str) or not value.strip():
        return True
    stripped = value.strip()
    if any(char.isdigit() for char in stripped):
        return True
    if _has_unbalanced_delimiters(stripped):
        return True
    if _has_excessive_isolated_letters(stripped):
        return True
    return False


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
    if _has_suspicious_name_shape(record.get("name")):
        return False
    if _has_suspicious_name_shape(record.get("source_name")):
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
