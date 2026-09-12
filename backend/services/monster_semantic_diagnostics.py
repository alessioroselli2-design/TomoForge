"""Privacy-safe semantic diagnostics for OCR-derived monster core fields.

These helpers are diagnostic-only: they never alter parser acceptance, review
status, provenance, or canonical data. They compare coarse numeric signatures
in memory and return booleans/counts only, never source values or OCR text.
"""

from __future__ import annotations

import re
from typing import Mapping

_INTEGER_RE = re.compile(r"\d+")


def _numeric_signature(value: object) -> tuple[int, ...]:
    """Return an in-memory numeric signature without retaining source text."""
    return tuple(int(token) for token in _INTEGER_RE.findall(str(value or "")))


def semantic_core_field_matches(
    left_attributes: Mapping[str, object],
    right_attributes: Mapping[str, object],
) -> dict[str, bool]:
    """Compare coarse monster core-field semantics without exposing values.

    AC and HP compare their leading numeric value. Speed compares its numeric
    sequence so harmless OCR/layout differences in labels or punctuation can be
    distinguished from a genuine movement-value disagreement. Missing numeric
    values never count as a semantic match.
    """
    left_ac = _numeric_signature(left_attributes.get("classe_armatura"))
    right_ac = _numeric_signature(right_attributes.get("classe_armatura"))
    left_hp = _numeric_signature(left_attributes.get("punti_ferita"))
    right_hp = _numeric_signature(right_attributes.get("punti_ferita"))
    left_speed = _numeric_signature(left_attributes.get("velocita"))
    right_speed = _numeric_signature(right_attributes.get("velocita"))

    return {
        "classe_armatura_semantic_match": bool(left_ac and right_ac and left_ac[0] == right_ac[0]),
        "punti_ferita_semantic_match": bool(left_hp and right_hp and left_hp[0] == right_hp[0]),
        "velocita_semantic_match": bool(left_speed and right_speed and left_speed == right_speed),
    }
