"""Privacy-safe diagnostics for residual OCR tokens in monster speed fields.

This module is diagnostic-only. It never changes parser acceptance, review state,
provenance, canonical data, or Supabase writes. Source values and residual token
text stay in process memory; returned values are booleans or aggregate integers.
"""

from __future__ import annotations

from typing import Mapping

from services.monster_name_diagnostics import compact_name_containment_match
from services.monster_residual_diagnostics import (
    _alphabetic_tokens,
    _extra_alphabetic_token_counter,
    _residual_normalized_pair,
)

_SPEED_FIELD = "velocita"


def speed_single_extra_token_profile(
    left_attributes: Mapping[str, object],
    right_attributes: Mapping[str, object],
) -> dict[str, bool]:
    """Classify one unambiguous extra speed token by length band and position."""
    result = {
        "velocita_residual_single_extra_alpha_token_len_3_to_6": False,
        "velocita_residual_single_extra_alpha_token_len_gt6": False,
        "velocita_residual_single_extra_alpha_token_internal": False,
    }

    pair = _residual_normalized_pair(
        _SPEED_FIELD,
        left_attributes,
        right_attributes,
    )
    if pair is None:
        return result

    left_tokens = _alphabetic_tokens(pair[0])
    right_tokens = _alphabetic_tokens(pair[1])
    extras, extras_on_right = _extra_alphabetic_token_counter(left_tokens, right_tokens)
    if sum(extras.values()) != 1:
        return result

    token = next(iter(extras))
    longer = right_tokens if extras_on_right else left_tokens
    shorter = left_tokens if extras_on_right else right_tokens
    if len(longer) != len(shorter) + 1:
        return result

    positions = [
        index
        for index, candidate in enumerate(longer)
        if candidate == token and longer[:index] + longer[index + 1 :] == shorter
    ]
    if len(positions) != 1:
        return result

    index = positions[0]
    token_length = len(token)
    result["velocita_residual_single_extra_alpha_token_len_3_to_6"] = (
        3 <= token_length <= 6
    )
    result["velocita_residual_single_extra_alpha_token_len_gt6"] = token_length > 6
    result["velocita_residual_single_extra_alpha_token_internal"] = (
        0 < index < len(longer) - 1
    )
    return result


def _subsequence_match_count_capped(
    longer: tuple[str, ...],
    shorter: tuple[str, ...],
    *,
    cap: int = 2,
) -> int:
    """Count token-preserving deletion paths, capped to avoid exposing detail."""
    if cap < 1 or len(shorter) > len(longer):
        return 0

    ways = [0] * (len(shorter) + 1)
    ways[0] = 1
    for token in longer:
        for index in range(len(shorter), 0, -1):
            if token == shorter[index - 1]:
                ways[index] = min(cap, ways[index] + ways[index - 1])
    return ways[-1]


def speed_multi_extra_token_profile(
    left_attributes: Mapping[str, object],
    right_attributes: Mapping[str, object],
) -> dict[str, bool]:
    """Classify multi-token or duplicate-ambiguous speed OCR residue.

    Signals are emitted only after the same residual semantic/numeric safety gates
    used by the other speed diagnostics. Token text never leaves this function.
    A duplicate is called ambiguous only when more than one token-preserving
    deletion path can reconstruct the shorter sequence from the longer sequence.
    """
    result = {
        "velocita_residual_extra_alpha_tokens_exactly_2": False,
        "velocita_residual_extra_alpha_tokens_3_or_more": False,
        "velocita_residual_duplicate_ambiguous": False,
    }

    pair = _residual_normalized_pair(
        _SPEED_FIELD,
        left_attributes,
        right_attributes,
    )
    if pair is None:
        return result

    left_tokens = _alphabetic_tokens(pair[0])
    right_tokens = _alphabetic_tokens(pair[1])
    extras, extras_on_right = _extra_alphabetic_token_counter(left_tokens, right_tokens)
    extra_count = sum(extras.values())
    if extra_count < 1:
        return result

    longer = right_tokens if extras_on_right else left_tokens
    shorter = left_tokens if extras_on_right else right_tokens
    if len(longer) - len(shorter) != extra_count:
        return result

    result["velocita_residual_extra_alpha_tokens_exactly_2"] = extra_count == 2
    result["velocita_residual_extra_alpha_tokens_3_or_more"] = extra_count >= 3
    result["velocita_residual_duplicate_ambiguous"] = (
        _subsequence_match_count_capped(longer, shorter, cap=2) > 1
    )
    return result


def speed_extra_token_agreement_counts(
    primary: list[dict],
    comparison: list[dict],
) -> dict[str, int]:
    """Return same-page containment counts without exposing OCR token text."""
    single_signals = (
        "len_3_to_6",
        "len_gt6",
        "internal",
    )
    multi_signals = (
        "extra_alpha_tokens_exactly_2",
        "extra_alpha_tokens_3_or_more",
        "duplicate_ambiguous",
    )
    single_counts = {signal: 0 for signal in single_signals}
    multi_counts = {signal: 0 for signal in multi_signals}

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

        for signal in single_signals:
            key = f"velocita_residual_single_extra_alpha_token_{signal}"
            single_counts[signal] += int(
                any(
                    speed_single_extra_token_profile(
                        left_attributes,
                        other.get("attributes") or {},
                    )[key]
                    for other in containment_matches
                )
            )

        for signal in multi_signals:
            key = f"velocita_residual_{signal}"
            multi_counts[signal] += int(
                any(
                    speed_multi_extra_token_profile(
                        left_attributes,
                        other.get("attributes") or {},
                    )[key]
                    for other in containment_matches
                )
            )

    result = {
        f"monster_containment_velocita_residual_single_extra_alpha_token_{signal}": value
        for signal, value in single_counts.items()
    }
    result.update(
        {
            f"monster_containment_velocita_residual_{signal}": value
            for signal, value in multi_counts.items()
        }
    )
    return result
