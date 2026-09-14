"""Privacy-safe residual diagnostics for OCR-derived monster core fields.

These helpers are diagnostic-only. They never change parser acceptance, review
state, provenance, or canonical data. Source values are compared only in memory;
returned data contains booleans or aggregate counts, never OCR text or values.
"""

from __future__ import annotations

import re
import unicodedata
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
_PARENTHETICAL_RE = re.compile(r"\(([^()]*)\)")
_MAX_RESIDUAL_TEXT_LENGTH = 256

_KNOWN_MANUAL_EXTRA_ALPHA_TOKENS = {
    "punti_ferita": frozenset(
        {
            "d",
            "dado",
            "dadi",
            "vita",
            "pf",
            "punti",
            "ferita",
            "ferite",
            "media",
            "medio",
            "totale",
            "hit",
            "points",
            "hp",
            "die",
            "dice",
        }
    ),
    "velocita": frozenset(
        {
            "m",
            "metro",
            "metri",
            "vel",
            "velocita",
            "velocità",
            "camminare",
            "cammino",
            "scalare",
            "arrampicarsi",
            "nuotare",
            "volare",
            "scavare",
            "fluttuare",
            "walk",
            "walking",
            "climb",
            "climbing",
            "swim",
            "swimming",
            "fly",
            "flying",
            "burrow",
            "burrowing",
            "hover",
            "ft",
            "foot",
            "feet",
        }
    ),
}


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


def _extra_alphabetic_token_counter(
    left: tuple[str, ...], right: tuple[str, ...]
) -> tuple[Counter[str], bool]:
    """Return strict multiset extras and which side owns them, without text output."""
    left_counts = Counter(left)
    right_counts = Counter(right)
    if left_counts == right_counts:
        return Counter(), False
    if left_counts <= right_counts:
        return right_counts - left_counts, True
    if right_counts <= left_counts:
        return left_counts - right_counts, False
    return Counter(), False


def _has_extra_alphabetic_tokens(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    """Detect a strict token-multiset containment in either direction."""
    extras, _ = _extra_alphabetic_token_counter(left, right)
    return bool(extras)


def _has_word_order_variation(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    """Detect reordered alphabetic tokens without fuzzy equivalence."""
    return bool(
        len(left) >= 2
        and len(right) >= 2
        and left != right
        and Counter(left) == Counter(right)
    )


def _extra_tokens_are_known_manual_labels(field: str, extras: Counter[str]) -> bool:
    """Require every residual token to belong to a conservative field allow-list."""
    known = _KNOWN_MANUAL_EXTRA_ALPHA_TOKENS.get(field, frozenset())
    return bool(extras and all(token in known for token in extras))


def _parenthetical_alpha_token_counter(value: object) -> Counter[str]:
    """Count alphabetic tokens inside parentheses in memory only."""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    tokens: Counter[str] = Counter()
    for group in _PARENTHETICAL_RE.findall(text):
        tokens.update(_alphabetic_tokens(group))
    return tokens


def _extra_tokens_are_parenthetical(extras: Counter[str], source_value: object) -> bool:
    """Return true only when every residual token occurs inside parentheses."""
    if not extras:
        return False
    return extras <= _parenthetical_alpha_token_counter(source_value)


def _single_extra_alpha_token_profile(
    left: tuple[str, ...], right: tuple[str, ...]
) -> tuple[bool, bool, bool]:
    """Classify one unambiguous extra token by short length and edge position.

    The token itself never leaves this helper. If there is more than one extra
    token instance, or removing the extra token could match in multiple places,
    all signals fail closed.
    """
    extras, extras_on_right = _extra_alphabetic_token_counter(left, right)
    if sum(extras.values()) != 1:
        return False, False, False

    token = next(iter(extras))
    longer = right if extras_on_right else left
    shorter = left if extras_on_right else right
    if len(longer) != len(shorter) + 1:
        return False, False, False

    positions = [
        index
        for index, candidate in enumerate(longer)
        if candidate == token and longer[:index] + longer[index + 1 :] == shorter
    ]
    if len(positions) != 1:
        return False, False, False

    index = positions[0]
    return len(token) < 3, index == 0, index == len(longer) - 1


def _has_non_alphanumeric_only_variation(left: str, right: str) -> bool:
    """Detect residuals caused only by punctuation, symbols, spaces, or format chars."""
    if not left or not right or left == right:
        return False
    left_skeleton = "".join(char for char in left if char.isalnum())
    right_skeleton = "".join(char for char in right if char.isalnum())
    return bool(left_skeleton and left_skeleton == right_skeleton)


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
        known_manual_label_extra_alpha_tokens = False
        parenthetical_extra_alpha_tokens = False
        single_extra_alpha_token_short_lt3 = False
        single_extra_alpha_token_prefix = False
        single_extra_alpha_token_suffix = False
        non_alphanumeric_only_variation = False

        if pair is not None:
            left, right = pair
            edit_distance = _bounded_levenshtein_distance(left, right, max_distance=3)
            left_tokens = _alphabetic_tokens(left)
            right_tokens = _alphabetic_tokens(right)
            extra_alpha_tokens = _has_extra_alphabetic_tokens(left_tokens, right_tokens)
            word_order_variation = _has_word_order_variation(left_tokens, right_tokens)

            extras, extras_on_right = _extra_alphabetic_token_counter(
                left_tokens,
                right_tokens,
            )
            if field in _KNOWN_MANUAL_EXTRA_ALPHA_TOKENS:
                known_manual_label_extra_alpha_tokens = _extra_tokens_are_known_manual_labels(
                    field,
                    extras,
                )
                source_value = (
                    right_attributes.get(field)
                    if extras_on_right
                    else left_attributes.get(field)
                )
                parenthetical_extra_alpha_tokens = _extra_tokens_are_parenthetical(
                    extras,
                    source_value,
                )
                (
                    single_extra_alpha_token_short_lt3,
                    single_extra_alpha_token_prefix,
                    single_extra_alpha_token_suffix,
                ) = _single_extra_alpha_token_profile(left_tokens, right_tokens)

            if field == "classe_armatura":
                non_alphanumeric_only_variation = _has_non_alphanumeric_only_variation(
                    left,
                    right,
                )

        result[f"{field}_residual_edit_distance_2_match"] = edit_distance == 2
        result[f"{field}_residual_edit_distance_3_match"] = edit_distance == 3
        result[f"{field}_residual_extra_alpha_tokens"] = extra_alpha_tokens
        result[f"{field}_residual_word_order_variation"] = word_order_variation
        result[f"{field}_residual_known_manual_label_extra_alpha_tokens"] = (
            known_manual_label_extra_alpha_tokens
        )
        result[f"{field}_residual_parenthetical_extra_alpha_tokens"] = (
            parenthetical_extra_alpha_tokens
        )
        result[f"{field}_residual_single_extra_alpha_token_short_lt3"] = (
            single_extra_alpha_token_short_lt3
        )
        result[f"{field}_residual_single_extra_alpha_token_prefix"] = (
            single_extra_alpha_token_prefix
        )
        result[f"{field}_residual_single_extra_alpha_token_suffix"] = (
            single_extra_alpha_token_suffix
        )
        result[f"{field}_residual_non_alphanumeric_only_variation"] = (
            non_alphanumeric_only_variation
        )

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
    refinement_counts = {
        "classe_armatura": {
            "non_alphanumeric_only_variation": 0,
        },
        "punti_ferita": {
            "known_manual_label_extra_alpha_tokens": 0,
            "parenthetical_extra_alpha_tokens": 0,
            "single_extra_alpha_token_short_lt3": 0,
            "single_extra_alpha_token_prefix": 0,
            "single_extra_alpha_token_suffix": 0,
        },
        "velocita": {
            "known_manual_label_extra_alpha_tokens": 0,
            "parenthetical_extra_alpha_tokens": 0,
            "single_extra_alpha_token_short_lt3": 0,
            "single_extra_alpha_token_prefix": 0,
            "single_extra_alpha_token_suffix": 0,
        },
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

            for signal in refinement_counts.get(field, {}):
                key = f"{field}_residual_{signal}"
                refinement_counts[field][signal] += int(
                    any(
                        residual_shape_core_field_matches(
                            left_attributes,
                            other.get("attributes") or {},
                        )[key]
                        for other in containment_matches
                    )
                )

    result = {
        f"monster_containment_{field}_residual_{signal}": counts[field][signal]
        for field in _CORE_FIELDS
        for signal in signals
    }
    result.update(
        {
            f"monster_containment_{field}_residual_{signal}": value
            for field, field_counts in refinement_counts.items()
            for signal, value in field_counts.items()
        }
    )
    return result
