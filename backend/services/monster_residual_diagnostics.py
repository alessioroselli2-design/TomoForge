"""Privacy-safe residual diagnostics for OCR-derived monster core fields.

These helpers are diagnostic-only. They never change parser acceptance, review
state, provenance, or canonical data. Source values are compared only in memory;
returned data contains booleans or aggregate counts, never OCR text or values.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Mapping

from services.monster_name_diagnostics import (
    compact_name_containment_match,
    compact_name_single_edit_match,
)
from services.monster_semantic_diagnostics import (
    _deterministic_normalized_value,
    _numeric_signature,
    deterministic_core_field_matches,
    semantic_core_field_matches,
)

_CORE_FIELDS = ("classe_armatura", "punti_ferita", "velocita")
_ALPHA_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_MAX_RESIDUAL_TEXT_LENGTH = 256


def _same_numeric_signature(left: object, right: object) -> bool:
    """Require every in-memory numeric token to agree before edit diagnostics."""
    left_numbers = _numeric_signature(left)
    right_numbers = _numeric_signature(right)
    return bool(left_numbers and right_numbers and left_numbers == right_numbers)


def _residual_normalized_pair(
    field: str,
    left_attributes: Mapping[str, object],
    right_attributes: Mapping[str, object],
) -> tuple[str, str] | None:
    """Return a bounded normalized residual pair only after all safety gates pass."""
    if field not in _CORE_FIELDS:
        return None

    raw_left = left_attributes.get(field)
    raw_right = right_attributes.get(field)
    semantic = semantic_core_field_matches(left_attributes, right_attributes)
    deterministic = deterministic_core_field_matches(left_attributes, right_attributes)
    left = _deterministic_normalized_value(field, raw_left)
    right = _deterministic_normalized_value(field, raw_right)

    if not (
        semantic.get(f"{field}_semantic_match", False)
        and _same_numeric_signature(raw_left, raw_right)
        and not deterministic.get(f"{field}_deterministic_match", False)
        and left
        and right
        and len(left) <= _MAX_RESIDUAL_TEXT_LENGTH
        and len(right) <= _MAX_RESIDUAL_TEXT_LENGTH
    ):
        return None
    return left, right


def _bounded_levenshtein_distance(left: str, right: str, max_distance: int = 3) -> int | None:
    """Return exact edit distance only when it is within a small fixed bound."""
    left = "".join(left.split())
    right = "".join(right.split())
    if not left or not right or left == right or max_distance < 1:
        return None
    if abs(len(left) - len(right)) > max_distance:
        return None

    if len(left) > len(right):
        left, right = right, left

    previous = list(range(len(left) + 1))
    for row_index, right_char in enumerate(right, start=1):
        current = [row_index]
        for column_index, left_char in enumerate(left, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column_index] + 1,
                    previous[column_index - 1] + int(left_char != right_char),
                )
            )
        if min(current) > max_distance:
            return None
        previous = current

    distance = previous[-1]
    return distance if 1 <= distance <= max_distance else None


def _alphabetic_tokens(value: str) -> tuple[str, ...]:
    """Return normalized alphabetic tokens in memory without exposing them."""
    return tuple(_ALPHA_TOKEN_RE.findall(value))


def _has_extra_alphabetic_tokens(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    """Detect a strict token-multiset containment in either direction."""
    left_counts = Counter(left)
    right_counts = Counter(right)
    if left_counts == right_counts:
        return False
    return bool(left_counts <= right_counts or right_counts <= left_counts)


def _has_word_order_variation(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    """Detect reordered alphabetic tokens without fuzzy equivalence."""
    return bool(
        len(left) >= 2
        and len(right) >= 2
        and left != right
        and Counter(left) == Counter(right)
    )


def residual_single_edit_core_field_matches(
    left_attributes: Mapping[str, object],
    right_attributes: Mapping[str, object],
) -> dict[str, bool]:
    """Identify one-edit OCR residue after conservative normalization.

    A field is counted only when its semantic diagnostic already agrees, every
    numeric token is identical, its deterministic normalized form still
    disagrees, and those two normalized forms are exactly one compact edit
    apart. This is intentionally diagnostic only: it does not relax the
    production agreement gate.
    """
    semantic = semantic_core_field_matches(left_attributes, right_attributes)
    deterministic = deterministic_core_field_matches(left_attributes, right_attributes)
    result: dict[str, bool] = {}

    for field in _CORE_FIELDS:
        raw_left = left_attributes.get(field)
        raw_right = right_attributes.get(field)
        left = _deterministic_normalized_value(field, raw_left)
        right = _deterministic_normalized_value(field, raw_right)
        result[f"{field}_residual_single_edit_match"] = bool(
            semantic[f"{field}_semantic_match"]
            and _same_numeric_signature(raw_left, raw_right)
            and not deterministic[f"{field}_deterministic_match"]
            and left
            and right
            and compact_name_single_edit_match(left, right)
        )

    return result


def residual_shape_core_field_matches(
    left_attributes: Mapping[str, object],
    right_attributes: Mapping[str, object],
) -> dict[str, bool]:
    """Classify residual core-field shape using bounded, diagnostic-only signals.

    Every signal fails closed unless semantic values agree, the full numeric
    sequence is identical, deterministic normalization still disagrees, and both
    normalized strings are non-empty and bounded. No source text is returned.
    """
    result: dict[str, bool] = {}

    for field in _CORE_FIELDS:
        pair = _residual_normalized_pair(field, left_attributes, right_attributes)
        edit_distance = None
        extra_alpha_tokens = False
        word_order_variation = False
        if pair is not None:
            left, right = pair
            edit_distance = _bounded_levenshtein_distance(left, right, max_distance=3)
            left_tokens = _alphabetic_tokens(left)
            right_tokens = _alphabetic_tokens(right)
            extra_alpha_tokens = _has_extra_alphabetic_tokens(left_tokens, right_tokens)
            word_order_variation = _has_word_order_variation(left_tokens, right_tokens)

        result[f"{field}_residual_edit_distance_2_match"] = edit_distance == 2
        result[f"{field}_residual_edit_distance_3_match"] = edit_distance == 3
        result[f"{field}_residual_extra_alpha_tokens"] = extra_alpha_tokens
        result[f"{field}_residual_word_order_variation"] = word_order_variation

    return result


def residual_single_edit_agreement_counts(
    primary: list[dict],
    comparison: list[dict],
) -> dict[str, int]:
    """Return aggregate-only residual counts for pilot diagnostics.

    The historical single-edit counters remain unchanged; additional residual
    shape counters are merged in parallel so existing pilot wiring can emit the
    new diagnostics without altering parser acceptance behavior.
    """
    exact_counts = {field: 0 for field in _CORE_FIELDS}
    containment_counts = {field: 0 for field in _CORE_FIELDS}
    containment_all_core = 0

    for record in primary:
        start_page = int(record.get("start_page") or 0)
        normalized_name = str(record.get("normalized_name") or "")
        same_page_matches = [
            other
            for other in comparison
            if int(other.get("start_page") or 0) == start_page
        ]
        exact_matches = [
            other
            for other in same_page_matches
            if str(other.get("normalized_name") or "") == normalized_name
        ]
        containment_matches = [
            other
            for other in same_page_matches
            if compact_name_containment_match(
                normalized_name,
                str(other.get("normalized_name") or ""),
            )
        ]
        left_attributes = record.get("attributes") or {}

        for field in _CORE_FIELDS:
            key = f"{field}_residual_single_edit_match"
            exact_counts[field] += int(
                any(
                    residual_single_edit_core_field_matches(
                        left_attributes,
                        other.get("attributes") or {},
                    )[key]
                    for other in exact_matches
                )
            )
            containment_counts[field] += int(
                any(
                    residual_single_edit_core_field_matches(
                        left_attributes,
                        other.get("attributes") or {},
                    )[key]
                    for other in containment_matches
                )
            )

        containment_all_core += int(
            any(
                all(
                    deterministic_core_field_matches(
                        left_attributes,
                        other.get("attributes") or {},
                    )[f"{field}_deterministic_match"]
                    or residual_single_edit_core_field_matches(
                        left_attributes,
                        other.get("attributes") or {},
                    )[f"{field}_residual_single_edit_match"]
                    for field in _CORE_FIELDS
                )
                for other in containment_matches
            )
        )

    result = {
        "monster_primary_with_same_page_containment_and_deterministic_or_single_edit_core_match": containment_all_core,
        "monster_containment_classe_armatura_residual_single_edit_match": containment_counts[
            "classe_armatura"
        ],
        "monster_containment_punti_ferita_residual_single_edit_match": containment_counts[
            "punti_ferita"
        ],
        "monster_containment_velocita_residual_single_edit_match": containment_counts["velocita"],
        "monster_exact_key_classe_armatura_residual_single_edit_match": exact_counts[
            "classe_armatura"
        ],
        "monster_exact_key_punti_ferita_residual_single_edit_match": exact_counts[
            "punti_ferita"
        ],
        "monster_exact_key_velocita_residual_single_edit_match": exact_counts["velocita"],
    }
    result.update(residual_shape_agreement_counts(primary, comparison))
    return result


def residual_shape_agreement_counts(
    primary: list[dict],
    comparison: list[dict],
) -> dict[str, int]:
    """Return containment-only residual-shape counts without source values."""
    signals = (
        "edit_distance_2_match",
        "edit_distance_3_match",
        "extra_alpha_tokens",
        "word_order_variation",
    )
    counts = {
        field: {signal: 0 for signal in signals}
        for field in _CORE_FIELDS
    }

    for record in primary:
        start_page = int(record.get("start_page") or 0)
        normalized_name = str(record.get("normalized_name") or "")
        containment_matches = [
            other
            for other in comparison
            if int(other.get("start_page") or 0) == start_page
            and compact_name_containment_match(
                normalized_name,
                str(other.get("normalized_name") or ""),
            )
        ]
        left_attributes = record.get("attributes") or {}

        for field in _CORE_FIELDS:
            for signal in signals:
                key = f"{field}_residual_{signal}"
                counts[field][signal] += int(
                    any(
                        residual_shape_core_field_matches(
                            left_attributes,
                            other.get("attributes") or {},
                        )[key]
                        for other in containment_matches
                    )
                )

    return {
        f"monster_containment_{field}_residual_{signal}": counts[field][signal]
        for field in _CORE_FIELDS
        for signal in signals
    }
