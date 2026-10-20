"""Fail-closed read-only source verification of the Tasha Steel Defender.

This is a distinct provenance record from the already-verified Eberron
Steel Defender. Historical raw OCR and all operational fields stay immutable.
Publisher's 2020 Eberron errata and Tasha English p20 independently corroborate
the formula; neither is a claim of successful OCR of the private Italian PDF.
"""

from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_5a08650dfd5d5eccb3664eeef39a100b"
SOURCE_FILE = "Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf"
CHECKSUM = "506347b5f5f5ae307b4a1550fe3280454227bc1c714de2eeba11c1a4b5447d2c"
RAW_SHA256 = "4bea793219b74cfa1660d211534975de4c4af32360b5027483f4182c2b78fd54"
HP_FORMULA = (
    "2 + il modificatore di Intelligenza del personaggio + cinque volte "
    "il livello da artefice del personaggio (il difensore ha un numero "
    "di Dadi Vita [d8] pari al livello da artefice del personaggio)"
)
ATTRS = {
    "classe_armatura": "15 (armatura naturale)",
    "punti_ferita": HP_FORMULA,
    "velocita": "12 m",
}
HISTORICAL_OCR_ATTRS = {
    "classe_armatura": "15 (armatura naturale)",
    "punti_ferita": "2",
    "velocita": "12 m",
}
SOURCE_REF = {"page": 20, "filename": SOURCE_FILE}


def assess_tasha_steel_defender_source(record: dict[str, Any] | None) -> dict[str, Any]:
    """Only the sealed, unchanged Tasha p20 Steel Defender may pass."""
    if not isinstance(record, dict):
        raise ValueError("target_record_missing")
    required = {
        "id": RECORD_ID,
        "name": "Difensore D'Acciaio",
        "source_name": "Difensore D'Acciaio",
        "reference_type": "monster",
        "source_language": "it",
        "source_key": SOURCE_FILE,
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": CHECKSUM,
        "attributes": ATTRS,
        "source_attributes": HISTORICAL_OCR_ATTRS,
        "review_corrections": {"_source_changed": True},
        "source_refs": [SOURCE_REF],
    }
    if any(record.get(k) != v for k, v in required.items()):
        raise ValueError("sealed_tasha_source_snapshot_drift")
    original = record.get("source_full_text")
    if not isinstance(original, str) or record.get("full_text") != original:
        raise ValueError("original_raw_text_mismatch")
    if hashlib.sha256(original.encode("utf-8")).hexdigest() != RAW_SHA256:
        raise ValueError("original_raw_sha256_drift")
    if monster_semantic_numeric_flags(ATTRS):
        raise ValueError("player_scaled_hp_or_ac_global_numeric_gate_failed")
    if not all(
        (
            original.startswith("Costrutto Medio Classe Armatura 15 (armatura naturale)"),
            "Punti Ferita " + HP_FORMULA in original,
            original.endswith("Velocità 12 m"),
            HP_FORMULA.startswith("2 + il modificatore di Intelligenza"),
            "cinque volte il livello da artefice" in HP_FORMULA,
            "Dadi Vita [d8]" in HP_FORMULA,
        )
    ):
        raise ValueError("registered_source_formula_or_semantics_drift")
    return {
        "status": "eligible_source_locked_status_only_review",
        "source": "Tasha p20",
        "source_page": 20,
        "attributes_unchanged": True,
        "original_ocr_preserved": True,
        "raw_text_preserved": True,
        "dynamic_hp_numeric_gate_passed": True,
        "writes": 0,
    }
