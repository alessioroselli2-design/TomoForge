"""Privacy-safe residual diagnostics for OCR-derived monster core fields.

These helpers are diagnostic-only. They never change parser acceptance, review
state, provenance, or canonical data. Source values are compared only in memory;
returned data contains booleans or aggregate counts, never OCR text or values.
"""

from __future__ import annotations

from typing import Mapping

from services.monster_name_diagnostics import (
    compact_name_containment_match,
    compact_name_single_edit_match,
)
from services.monster_semantic_diagnostics import (
    _deterministic_normalized_value,
    deterministic_core_field_matches,
    semantic_core_field_matches,
)

_CORE_FIELDS = ("classe_armatura", "punti_ferita", "velocita")


def residual_single_edit_core_field_matches(
    left_attributes: Mapping[str, object],
    right_attributes: Mapping[str, object],
) -> dict[str, bool]:
    """Identify one-edit OCR residue after conservative normalization.

    A field is counted only when its semantic diagnostic already agrees, its
    deterministic normalized form still disagrees, and those two normalized
    forms are exactly one compact edit apart. This is intentionally diagnostic
    only: it does not relax the production agreement gate.
    """
    semantic = semantic_core_field_matches(left_attributes, right_attributes)
    deterministic = deterministic_core_field_matches(left_attributes, right_attributes)
    result: dict[str, bool] = {}

    for field in _CORE_FIELDS:
        left = _deterministic_normalized_value(field, left_attributes.get(field))
        right = _deterministic_normalized_value(field, right_attributes.get(field))
        result[f"{field}_residual_single_edit_match"] = bool(
            semantic[f"{field}_semantic_match"]
            and not deterministic[f"{field}_deterministic_match"]
            and left
            and right
            and compact_name_single_edit_match(left, right)
        )

    return result


def residual_single_edit_agreement_counts(
    primary: list[dict],
    comparison: list[dict],
) -> dict[str, int]:
    """Return aggregate-only one-edit residual counts for pilot diagnostics."""
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

    return {
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
