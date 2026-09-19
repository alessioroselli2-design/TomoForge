"""Privacy-safe semantic diagnostics for OCR-derived monster core fields.

These helpers are diagnostic-only: they never alter parser acceptance, review
status, provenance, or canonical data. They compare coarse or deterministically
normalized signatures in memory and return booleans/counts only, never source
values or OCR text.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Mapping

_INTEGER_RE = re.compile(r"\d+")
_FIELD_PREFIXES = {
    "classe_armatura": re.compile(
        r"^(?:classe\s+armatura|ca)(?=$|[\s:\-])\s*[:\-]?\s*",
        re.IGNORECASE,
    ),
    "punti_ferita": re.compile(
        r"^(?:punti\s+ferita|pf)(?=$|[\s:\-])\s*[:\-]?\s*",
        re.IGNORECASE,
    ),
    "velocita": re.compile(
        r"^(?:velocit[aà]|vel)(?=$|[\s:\-])\s*[:\-]?\s*",
        re.IGNORECASE,
    ),
}
_PUNCTUATION_RE = re.compile(r"[()\[\]{},;:/|]")
_DICE_RE = re.compile(r"(?<=\d)\s*d\s*(?=\d)", re.IGNORECASE)
_SIGN_RE = re.compile(r"\s*([+\-])\s*")
_METERS_RE = re.compile(r"\bmetri?\b", re.IGNORECASE)
_SPACE_BEFORE_M_RE = re.compile(r"(?<=\d)\s+m\b", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")


def _numeric_signature(value: object) -> tuple[int, ...]:
    """Return an in-memory numeric signature without retaining source text."""
    return tuple(int(token) for token in _INTEGER_RE.findall(str(value or "")))


def _deterministic_normalized_value(field: str, value: object) -> str | None:
    """Normalize presentation-only OCR differences while failing closed.

    Only deterministic, field-scoped cleanup is applied: Unicode compatibility,
    known field-label prefixes delimited by whitespace/punctuation/end-of-string,
    common punctuation, meter spelling, dice spacing, sign spacing, and
    whitespace. Unknown words are preserved, so unexpected OCR text cannot
    disappear and accidentally create a match. Values with no digits are
    rejected instead of being considered equal.
    """
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    if not text:
        return None

    prefix = _FIELD_PREFIXES.get(field)
    if prefix is None:
        return None
    text = prefix.sub("", text, count=1)
    text = _METERS_RE.sub("m", text)
    text = _PUNCTUATION_RE.sub(" ", text)
    text = _DICE_RE.sub("d", text)
    text = _SIGN_RE.sub(r"\1", text)
    text = _SPACE_BEFORE_M_RE.sub("m", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    if not text or not _INTEGER_RE.search(text):
        return None
    return text


def deterministic_core_field_matches(
    left_attributes: Mapping[str, object],
    right_attributes: Mapping[str, object],
) -> dict[str, bool]:
    """Compare core fields after conservative deterministic text cleanup.

    This is diagnostic-only. It intentionally preserves unknown words and never
    participates in record acceptance or review-state changes.
    """
    result: dict[str, bool] = {}
    for field in ("classe_armatura", "punti_ferita", "velocita"):
        left = _deterministic_normalized_value(field, left_attributes.get(field))
        right = _deterministic_normalized_value(field, right_attributes.get(field))
        result[f"{field}_deterministic_match"] = bool(left and right and left == right)
    return result


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
        "classe_armatura_semantic_match": bool(
            left_ac and right_ac and left_ac[0] == right_ac[0]
        ),
        "punti_ferita_semantic_match": bool(
            left_hp and right_hp and left_hp[0] == right_hp[0]
        ),
        "velocita_semantic_match": bool(
            left_speed and right_speed and left_speed == right_speed
        ),
    }
