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
CORRUPTED_ENTITY_NAME_FLAG = "corrupted_entity_name"

_AC_VALUE_RE = re.compile(r"^\s*(\d{1,2})\b")
_DICE_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])\d+d\d+(?![A-Za-z0-9])", re.IGNORECASE)
_HP_DICE_EXPRESSION_RE = re.compile(
    r"^\s*(\d+)\s*\(\s*(\d+)d(\d+)\s*([+-]\s*\d+)?\s*\)\s*$",
    re.IGNORECASE,
)
# Examples intentionally rejected: ``1 3d8``, ``3 d8``, ``3d 8``, ``1 28``.
_SPLIT_NUMBER_RE = re.compile(r"\b\d+\s+\d+\b")
_SPLIT_HIT_DICE_COUNT_RE = re.compile(r"\b\d+\s+\d+d\d+\b", re.IGNORECASE)
_SPLIT_DICE_RE = re.compile(r"(?:\b\d+\s+d\d+\b|\b\d+d\s+\d+\b)", re.IGNORECASE)
# Reject a split inside the die-face number itself, for example ``4d1 2`` for
# ``4d12``. Without this check ``4d1`` looks like a superficially valid token.
_SPLIT_DICE_FACES_RE = re.compile(r"\b\d+d\d+\s+\d+\b", re.IGNORECASE)
# Typical OCR confusions in the dice token, for example ``32dl0`` for ``32d10``.
_OCR_DICE_LETTER_RE = re.compile(r"\b\d+d[il|]+\d*\b", re.IGNORECASE)

# Heading detector runs on a compact ASCII view of the name. This makes
# ``C A P I T O L O 6`` and ``C A P Itolo 6`` both become ``capitolo6``.
# ``passo`` deliberately requires following Arabic digits to avoid false
# positives on legitimate D&D names such as "Passo Velato".
_ENTITY_TITLE_COMPACT_RE = re.compile(
    r"^(?:"
    r"capitolo(?:\d+|[ivxlcdm]+)?|"
    r"passo\d+|"
    r"appendice(?:[a-z0-9]+)?|"
    r"tabella(?:\d+|[ivxlcdm]+)?|"
    r"statistichedeimostri(?:pergradodisfida)?"
    r")",
    re.IGNORECASE,
)

# Monster identity sanity is deliberately stricter than normal title parsing.
# Apostrophes/hyphens remain valid for names such as Graz'Zt, Fraz-Urb'Luu,
# T'Lincalli and Yuan-Ti. These characters are strong OCR-noise indicators in
# a monster name and should never reach source-guided mutation unattended.
_SUSPICIOUS_MONSTER_NAME_CHAR_RE = re.compile(r"[:$|_]")
_SUSPICIOUS_MONSTER_PUNCT_RUN_RE = re.compile(
    r"[^\w\s'’\-]{2,}",
    re.UNICODE,
)


def _compact_entity_name(name: Any) -> str:
    """Return a diacritic-free, punctuation/whitespace-free comparison key."""
    text = unicodedata.normalize("NFKD", str(name or ""))
    ascii_text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", ascii_text.casefold())


def _max_single_letter_token_run(name: Any) -> int:
    """Return longest run of standalone alphabetic one-letter OCR tokens."""
    text = unicodedata.normalize("NFKC", str(name or ""))
    longest = 0
    current = 0
    for raw_token in text.split():
        token = raw_token.strip('.,;!?()[]{}<>"“”')
        if len(token) == 1 and token.isalpha():
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


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


def monster_identity_sanity_flags(name: Any) -> set[str]:
    """Flag monster names that look structurally corrupted by OCR.

    This is not a fuzzy spellchecker. It only catches strong structural noise:
    explicit suspicious punctuation, runs of unusual punctuation, or at least
    four consecutive standalone single-letter alphabetic tokens such as
    ``F o R M E``. Legitimate apostrophes and hyphens are intentionally allowed.
    Missing names are left to the existing structural validation path instead
    of being reclassified by this OCR-specific gate.
    """
    text = unicodedata.normalize("NFKC", str(name or "")).strip()
    if not text:
        return set()
    if _SUSPICIOUS_MONSTER_NAME_CHAR_RE.search(text):
        return {CORRUPTED_ENTITY_NAME_FLAG}
    if _SUSPICIOUS_MONSTER_PUNCT_RUN_RE.search(text):
        return {CORRUPTED_ENTITY_NAME_FLAG}
    if _max_single_letter_token_run(text) >= 4:
        return {CORRUPTED_ENTITY_NAME_FLAG}
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
    has_split_dice_faces = bool(_SPLIT_DICE_FACES_RE.search(hp_text))
    has_ocr_dice_letters = bool(_OCR_DICE_LETTER_RE.search(hp_text))
    hp_expression = _HP_DICE_EXPRESSION_RE.fullmatch(hp_text)
    mathematically_coherent = False
    if hp_expression:
        average = int(hp_expression.group(1))
        dice_count = int(hp_expression.group(2))
        die_size = int(hp_expression.group(3))
        modifier = int((hp_expression.group(4) or "0").replace(" ", ""))
        expected_average = (dice_count * (die_size + 1)) // 2 + modifier
        mathematically_coherent = average == expected_average
    if (
        not dice_token_ok
        or has_split_number
        or has_split_hit_dice_count
        or has_split_dice
        or has_split_dice_faces
        or has_ocr_dice_letters
        or not mathematically_coherent
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
        flags.update(monster_identity_sanity_flags(record.get("name")))
        flags.update(monster_semantic_numeric_flags(record.get("attributes") or {}))

    gated["review_flags"] = sorted(flags)
    gated["review_status"] = "pending"
    return gated
