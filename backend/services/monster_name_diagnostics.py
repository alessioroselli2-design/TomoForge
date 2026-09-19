"""Privacy-safe diagnostics for OCR-derived monster names.

These helpers are diagnostic-only. They must never alter parser acceptance,
review state, provenance, or canonical data. Returned values are booleans only;
raw OCR names are never persisted by this module.
"""

from __future__ import annotations


def _compact(value: object) -> str:
    return "".join(str(value or "").split())


def compact_name_boundary_match(
    left_normalized: object, right_normalized: object
) -> bool:
    """Detect whether normalized names differ only by OCR word boundaries.

    ``normalized_name`` values are already accent/punctuation insensitive. This
    helper removes ASCII whitespace only, so it can distinguish a likely OCR
    split such as ``"most ro"`` from real character substitutions, missing
    words, or other textual differences. Empty names never match.
    """
    left = _compact(left_normalized)
    right = _compact(right_normalized)
    return bool(left and right and left == right)


def compact_name_single_edit_match(
    left_normalized: object, right_normalized: object
) -> bool:
    """Return True only when compact normalized names are one edit apart.

    This is diagnostic-only and intentionally does not perform fuzzy matching.
    After removing whitespace, it recognizes exactly one insertion, deletion,
    or substitution. Exact matches, empty values, and distances greater than one
    return False. No source text is returned or persisted.
    """
    left = _compact(left_normalized)
    right = _compact(right_normalized)
    if not left or not right or left == right or abs(len(left) - len(right)) > 1:
        return False

    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1

    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    short_index = 0
    long_index = 0
    edits = 0
    while short_index < len(shorter) and long_index < len(longer):
        if shorter[short_index] == longer[long_index]:
            short_index += 1
            long_index += 1
            continue
        edits += 1
        if edits > 1:
            return False
        long_index += 1

    if long_index < len(longer):
        edits += 1
    return edits == 1


def compact_name_containment_match(
    left_normalized: object, right_normalized: object
) -> bool:
    """Detect a strict compact-name containment relationship.

    This diagnostic identifies likely missing or extra OCR fragments without
    fuzzy matching. Whitespace is removed first; exact matches and empty values
    never match. The shorter compact name must contain at least four characters
    to avoid classifying tiny OCR fragments as meaningful containment.
    """
    left = _compact(left_normalized)
    right = _compact(right_normalized)
    if not left or not right or left == right:
        return False
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    return len(shorter) >= 4 and shorter in longer
