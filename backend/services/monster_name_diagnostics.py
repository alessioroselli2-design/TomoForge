"""Privacy-safe diagnostics for OCR-derived monster names.

These helpers are diagnostic-only. They must never alter parser acceptance,
review state, provenance, or canonical data. Returned values are booleans only;
raw OCR names are never persisted by this module.
"""

from __future__ import annotations


def compact_name_boundary_match(left_normalized: object, right_normalized: object) -> bool:
    """Detect whether normalized names differ only by OCR word boundaries.

    ``normalized_name`` values are already accent/punctuation insensitive. This
    helper removes ASCII whitespace only, so it can distinguish a likely OCR
    split such as ``"most ro"`` from real character substitutions, missing
    words, or other textual differences. Empty names never match.
    """
    left = "".join(str(left_normalized or "").split())
    right = "".join(str(right_normalized or "").split())
    return bool(left and right and left == right)
