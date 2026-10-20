"""Sealed, source-reviewed editorial discrepancy for one Eberron monster.

This does not disable OCR/HP gates or verify records automatically. It produces
a fail-closed candidate for an explicitly documented manual adjudication.
"""

from __future__ import annotations

from typing import Any

from services.ocr_semantic_gates import (
    HP_FORMAT_ERROR_FLAG,
    monster_semantic_numeric_flags,
)

RECORD_ID = "ref_808e61bb52e050a8a7576b0941cfb3b9"
SOURCE_ID = "erlw_2019_it"
SOURCE_CHECKSUM = "9822846d066cff3e847352cd6c1962bbc26b5de1ecec1070cd4e912c62acf685"
ITALIAN_RAW_HP = "19 (3d8 + 8)"
ENGLISH_CORRECTED_HP = "19 (3d8 + 6)"
SEALED_ATTRIBUTES = {
    "classe_armatura": "14 (armatura di cuoio)",
    "punti_ferita": ITALIAN_RAW_HP,
    "velocita": "9 m",
}
EXPECTED_FLAGS = ["ocr_da_verificare", "source_guided_repair"]
EXPECTED_CORE_EXCERPT = (
    "Classe Armatura 14 (armatura di cuoio) "
    "Punti Ferita 19 (3d8 + 8) Velocità 9 m"
)


def assess_morfico_editorial_discrepancy(record: dict[str, Any]) -> dict[str, Any]:
    """Only admit the exact manually reviewed Eberron p321 source snapshot."""
    if not isinstance(record, dict):
        raise ValueError("record_missing")
    if (
        record.get("id") != RECORD_ID
        or record.get("name") != "Morfico"
        or record.get("reference_type") != "monster"
        or record.get("review_status") != "pending"
        or record.get("canonical_id") is not None
        or record.get("source_text_checksum") != SOURCE_CHECKSUM
        or record.get("review_flags") != EXPECTED_FLAGS
        or record.get("attributes") != SEALED_ATTRIBUTES
    ):
        raise ValueError("sealed_record_snapshot_drift")

    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1:
        raise ValueError("source_reference_count_drift")
    ref = refs[0]
    if not isinstance(ref, dict) or not all(
        (
            ref.get("logical_source_id") == SOURCE_ID,
            ref.get("page") == 321,
            ref.get("logical_page") == 321,
            ref.get("source_status") == "active",
            ref.get("source_role") == "authority",
            ref.get("authority_class") == "licensed_translation",
            ref.get("filename") == "618795464-Eberron.pdf",
            ref.get("ruleset") == "2014",
        )
    ):
        raise ValueError("registered_provenance_drift")
    if EXPECTED_CORE_EXCERPT not in str(record.get("full_text") or ""):
        raise ValueError("original_italian_text_drift")

    if monster_semantic_numeric_flags(SEALED_ATTRIBUTES) != {HP_FORMAT_ERROR_FLAG}:
        raise ValueError("italian_source_error_not_isolated")
    corrected = dict(SEALED_ATTRIBUTES)
    corrected["punti_ferita"] = ENGLISH_CORRECTED_HP
    if monster_semantic_numeric_flags(corrected):
        raise ValueError("corrected_core_failed_numeric_gates")

    # 3d8 + (3 * CON +2) = floor(3*9/2) + 6 = 19.
    if 3 * 2 != 6 or (3 * (8 + 1)) // 2 + 6 != 19:
        raise ValueError("english_constitution_hp_disagrees")
    return {
        "status": "eligible_for_source_editorial_adjudication",
        "record_id": RECORD_ID,
        "source_id": SOURCE_ID,
        "physical_page": 321,
        "original_italian_hp": ITALIAN_RAW_HP,
        "corrected_english_hp": ENGLISH_CORRECTED_HP,
        "core_attributes": corrected,
        "all_original_attributes_except_hp_preserved": True,
        "math_gate_active_and_passed": True,
        "requires_explicit_editorial_review": True,
    }
