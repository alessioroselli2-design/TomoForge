"""Fail-closed exact-source review for Eberron Italian Tarkanan Assassin only.

The ordinary OCR pair disagrees about presentation of AC/speed despite
exactly matching numeric values. No OCR gates are changed or bypassed.
This source adjudication only accepts the immutable registered DB snapshot,
plus independently corroborated English original core.
"""

from __future__ import annotations

from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_ab2cf767c3f25e00a1e4720ef6c01d44"
SOURCE_CHECKSUM = "33c3843afcd29a46b03ecc70bca51365849897d644d2df975693e7afd2c1e2ca"
ATTRIBUTES = {
    "classe_armatura": "15 (cuoio borchiato)",
    "punti_ferita": "45 (7d8 + 14)",
    "velocita": "9 m",
}
ITALIAN_RAW = (
    "Umanoide Medio (qualsiasi razza), qualsiasi a/lineamento non buono "
    "Classe Armatura 15 (cuoio borchiato) Punti Ferita 45 (7d8 + 14) "
    "Velocità 9 m"
)


def assess_tarkanan_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Status-only eligibility from two exact active Italian authority pages."""
    if not isinstance(record, dict):
        raise ValueError("missing_source_record")
    if (
        record.get("id") != RECORD_ID
        or record.get("name") != "Assassino Tarkanan"
        or record.get("reference_type") != "monster"
        or record.get("review_status") != "pending"
        or record.get("canonical_id") is not None
        or record.get("review_flags") != []
        or record.get("source_text_checksum") != SOURCE_CHECKSUM
        or record.get("attributes") != ATTRIBUTES
        or record.get("full_text") != ITALIAN_RAW
    ):
        raise ValueError("source_record_snapshot_drift")

    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 2:
        raise ValueError("source_reference_count_drift")
    if sorted(ref.get("page") for ref in refs if isinstance(ref, dict)) != [317, 318]:
        raise ValueError("registered_pages_drift")
    for ref in refs:
        if not isinstance(ref, dict) or not all(
            (
                ref.get("logical_page") == ref.get("page"),
                ref.get("logical_source_id") == "erlw_2019_it",
                ref.get("source_status") == "active",
                ref.get("source_role") == "authority",
                ref.get("authority_class") == "licensed_translation",
                ref.get("filename") == "618795464-Eberron.pdf",
                ref.get("ruleset") == "2014",
            )
        ):
            raise ValueError("source_authority_drift")
    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("core_numeric_gate_rejected")
    if (7 * (8 + 1)) // 2 + 14 != 45:
        raise ValueError("hit_dice_arithmetic_disagrees")
    return {
        "status": "eligible_status_only_source_review",
        "source_id": "erlw_2019_it",
        "registered_pages": [317, 318],
        "original_attributes_unchanged": True,
        "numeric_gates_passed": True,
        "source_snapshot_unchanged": True,
        "separate_editorial_adjudication_required": True,
    }
