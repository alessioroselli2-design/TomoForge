"""Read-only registered-source review: Lince Gigante, Bigby IT physical p167.

This remains separate from ordinary paired OCR PR #432, which did NOT pass.
The Italian full_text contains an OCR-space artifact in CA ("1 4").
Neither this artifact nor any original field is altered during audit.
"""
from __future__ import annotations
from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_63424c86d98354efb93e1c6f03edad15"
SOURCE_CHECKSUM = "f393d3802ceff6e2fc00f8239d9a603e280ee15a6b6c76587c568ae19e10f875"
ATTRIBUTES = {
    "classe_armatura": "14",
    "punti_ferita": "22 (4d8 + 4)",
    "velocita": "9 m, scalare 9 m",
}
ITALIAN_RAW = (
    "Folletto Medio, generalmente neutrale Classe Armatura 1 4 "
    "Punti Ferita 22 (4d8 + 4) Velocità 9 m, scalare 9 m"
)
# English original, Bigby Presents: Glory of the Giants, printed p151.
# Giant Lynx: AC 14; HP 22 (4d8+4); Speed 30ft, climb 30ft.
ENGLISH_CORE = (14, 22, 4, 8, 4, 30, 30)

def assess_lince_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless the one active official registered source matches exactly."""
    if not isinstance(record, dict):
        raise ValueError("missing_registered_record")
    if (
        record.get("id") != RECORD_ID
        or record.get("name") != "Lince Gigante"
        or record.get("reference_type") != "monster"
        or record.get("review_status") != "pending"
        or record.get("canonical_id") is not None
        or record.get("review_flags") != ["ocr_da_verificare", "source_guided_repair"]
        or record.get("source_text_checksum") != SOURCE_CHECKSUM
        or record.get("attributes") != ATTRIBUTES
        or record.get("full_text") != ITALIAN_RAW
    ):
        raise ValueError("registered_snapshot_drift")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1:
        raise ValueError("authority_source_count_drift")
    ref = refs[0]
    if not isinstance(ref, dict) or not all(
        (
            ref.get("page") == 167,
            ref.get("logical_page") == 167,
            ref.get("logical_source_id") == "bgg_2023_it",
            ref.get("source_status") == "active",
            ref.get("source_role") == "authority",
            ref.get("authority_class") == "licensed_translation",
            ref.get("filename") == "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf",
            ref.get("source_title") == "Bigby Presenta: La Gloria dei Giganti",
            ref.get("ruleset") == "2014",
        )
    ):
        raise ValueError("registered_source_authority_drift")
    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("numeric_gate_rejected")
    ac, hp, dice_count, die_size, modifier, walk_ft, climb_ft = ENGLISH_CORE
    if (
        ac != 14
        or hp != 22
        or (dice_count * (die_size + 1)) // 2 + modifier != hp
        or (walk_ft, climb_ft) != (30, 30)
        or ATTRIBUTES["classe_armatura"] != "14"
        or ATTRIBUTES["punti_ferita"] != "22 (4d8 + 4)"
        or ATTRIBUTES["velocita"] != "9 m, scalare 9 m"
    ):
        raise ValueError("english_original_core_disagreement")
    return {
        "status": "eligible_status_only_source_review",
        "source_id": "bgg_2023_it",
        "registered_pages": [167],
        "original_attributes_unchanged": True,
        "numeric_gates_passed": True,
        "source_snapshot_unchanged": True,
        "separate_editorial_adjudication_required": True,
    }
