"""Fail-closed source-review for Bigby Italian Tagliafuoco (Firegaunt).

No writes; no changes to original source text or global math/OCR gates.
"""
from __future__ import annotations
from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_7195ffa044df51859e9850723d172587"
SOURCE_CHECKSUM = "467c8cbaffb78c27b8b48d8484ee80efaf2125a76a7ec74039a527991cef6cd1"
ITALIAN_RAW = (
    "Non morto Enorme, generalmente legale malvagio Classe Armatura 1 5 "
    "(armatura a piastre danneggiata) Punti Ferita 1 75 (14dl 2 + 84) "
    "Velocità 12 m"
)
ATTRIBUTES = {
    "classe_armatura": "15 (armatura a piastre danneggiata)",
    "punti_ferita": "175 (14d12 + 84)",
    "velocita": "12 m",
}


def assess_tagliafuoco_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Only exact registered authority and original statistical fields qualify."""
    if not isinstance(record, dict) or not all((
        record.get("id") == RECORD_ID,
        record.get("name") == "Tagliafuoco",
        record.get("reference_type") == "monster",
        record.get("review_status") == "pending",
        record.get("canonical_id") is None,
        record.get("review_flags") == ["ocr_da_verificare", "source_guided_repair"],
        record.get("source_text_checksum") == SOURCE_CHECKSUM,
        record.get("attributes") == ATTRIBUTES,
        record.get("full_text") == ITALIAN_RAW,
    )):
        raise ValueError("sealed_source_snapshot_drift")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1 or not isinstance(refs[0], dict):
        raise ValueError("registered_authority_count_drift")
    ref = refs[0]
    if not all((
        ref.get("page") == 183,
        ref.get("logical_page") == 183,
        ref.get("logical_source_id") == "bgg_2023_it",
        ref.get("source_role") == "authority",
        ref.get("source_status") == "active",
        ref.get("authority_class") == "licensed_translation",
        ref.get("ruleset") == "2014",
        ref.get("source_title") == "Bigby Presenta: La Gloria dei Giganti",
        ref.get("filename") == "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf",
    )):
        raise ValueError("authority_page_or_file_drift")
    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("global_numeric_gate_failed")
    # Independently corroborated English Firegaunt, Bigby original p137:
    # AC15 damaged plate, HP175 (14d12+84), 40ft speed (12m).
    if 14 * 6 != 84 or (14 * (12 + 1)) // 2 + 84 != 175:
        raise ValueError("hit_dice_math_failed")
    return {
        "status": "eligible_status_only_source_review",
        "source": "bgg_2023_it",
        "page": 183,
        "attributes_unchanged": True,
        "numeric_gates_passed": True,
        "raw_text_preserved": True,
    }
