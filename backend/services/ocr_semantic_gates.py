"""Fail-closed semantic/numeric gates for OCR-derived reference records.

The helpers in this module never repair or canonicalize OCR values. They only
add review flags and force OCR-derived records back to a non-approved state.
This keeps provenance intact and ensures suspicious values cannot become
trusted merely because parsing succeeded.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

OCR_REVIEW_FLAG = "ocr_da_verificare"
CA_OUT_OF_BOUNDS_FLAG = "CA_out_of_bounds"
CA_FORMAT_ERROR_FLAG = "CA_format_error"
HP_FORMAT_ERROR_FLAG = "HP_format_error"
INVALID_ENTITY_TITLE_FLAG = "invalid_entity_title"

_AC_VALUE_RE = re.compile(r"^\s*(\d{1,2})\b")
_DICE_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])\d+d\d+(?![A-Za-z0-9])", re.IGNORECASE)
# Examples intentionally rejected: ``1 3d8``, ``3 d8``, ``3d 8``, ``1 28``.
_SPLIT_NUMBER_RE = re.compile(r"\b\d+\s+\d+\b")
_SPLIT_HIT_DICE_COUNT_RE = re.compile(r"\b\d+\s+\d+d\d+\b", re.IGNORECASE)
_SPLIT_DICE_RE = re.compile(r"(?:\b\d+\s+d\d+\b|\b\d+d\s+\d+\b)", re.IGNORECASE)
# Typical OCR confusions in the dice token, for example ``32dl0`` for ``32d10``.
_OCR_DICE_LETTER_RE = re.compile(r"\b\d+d[il|]+\d*\b", re.IGNORECASE)

# Heading detector runs on a compact ASCII view of the name. This makes
# ``C A P I T O L O 6`` and ``C A P Itolo 6`` both become ``capitolo6``.
# ``passo`` deliberately requires a following number/Roman numeral to avoid
# false positives on legitimate D&D names such as "Passo Velato".
_ENTITY_TITLE_COMPACT_RE = re.compile(
    r"^(?:"
    r"capitolo(?:\d+|[ivxlcdm]+)?|"
    r"passo(?:\d+|[ivxlcdm]+)|"
    r"appendice(?:[a-z0-9]+)?|"
    r"tabella(?:\d+|[ivxlcdm]+)?|"
    r"statistichedeimostri(?:pergradodisfida)?"
    r")",
    re.IGNORECASE,
)


def _compact_entity_name(name: Any) -> str:
    """Return a diacritic-free, punctuation/whitespace-free comparison key."""
    text = unicodedata.normalize("NFKD", str(name or ""))
    ascii_text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", ascii_text.casefold())


def entity_name_semantic_flags(name: Any) -> set[str]:
    """Flag manual headings accidentally parsed as library entities.

    The gate is intentionally narrow: it recognizes strong heading prefixes
    and OCR letter-spacing variants, but does not attempt fuzzy correction or
    semantic guessing of arbitrary entity names.
    """
    compact = _compact_entity_name(name)
    if compact and _ENTITY_TITLE_COMPACT_RE.match(compact):
        return {INVALID_ENTITY_TITLE_FLAG}
    return set()


def monster_semantic_numeric_flags(attributes: dict[str, Any] | None) -> set[str]:
    """Return anomaly flags for a parsed monster without changing source data."""
    attributes = attributes or {}
    flags: set[str] = set()

    ac_text = str(attributes.get("classe_armatura") or "").strip()
    ac_match = _AC_VALUE_RE.match(ac_text)
    if not ac_match:
        # Missing/unparseable AC is also fail-closed, but remains distinct from
        # the explicit numeric bounds requested for parseable values.
        flags.add(CA_FORMAT_ERROR_FLAG)
    else:
        armor_class = int(ac_match.group(1))
        if armor_class < 5 or armor_class > 30:
            flags.add(CA_OUT_OF_BOUNDS_FLAG)

    hp_text = str(attributes.get("punti_ferita") or "").strip()
    dice_token_ok = bool(_DICE_TOKEN_RE.search(hp_text))
    has_split_number = bool(_SPLIT_NUMBER_RE.search(hp_text))
    has_split_hit_dice_count = bool(_SPLIT_HIT_DICE_COUNT_RE.search(hp_text))
    has_split_dice = bool(_SPLIT_DICE_RE.search(hp_text))
    has_ocr_dice_letters = bool(_OCR_DICE_LETTER_RE.search(hp_text))
    if (
        not dice_token_ok
        or has_split_number
        or has_split_hit_dice_count
        or has_split_dice
        or has_ocr_dice_letters
    ):
        flags.add(HP_FORMAT_ERROR_FLAG)

    return flags


def apply_ocr_review_gates(record: dict[str, Any]) -> dict[str, Any]:
    """Return an OCR record forced into review, with deterministic anomaly flags.

    ``review_status='pending'`` is used because the live Supabase constraint
    currently accepts ``pending/verified/needs_review``; ``ocr_da_verificare``
    remains a durable review flag rather than a database status value.
    """
    gated = dict(record)
    flags = {str(flag) for flag in (record.get("review_flags") or [])}
    flags.add(OCR_REVIEW_FLAG)
    flags.update(entity_name_semantic_flags(record.get("name")))

    if record.get("reference_type") == "monster":
        flags.update(monster_semantic_numeric_flags(record.get("attributes") or {}))

    gated["review_flags"] = sorted(flags)
    gated["review_status"] = "pending"
    return gated
