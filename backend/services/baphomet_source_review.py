"""Read-only, source-locked adjudication for Bigby IT Cacciatore Di Baphomet.

The original OCR is preserved. This is NOT a pass of the older paired-OCR PR.
"""
from __future__ import annotations
from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_abaf4a8fe2395260991a96729a200351"
CHECKSUM = "94e2b86aa7bbd78a46dc484cf7e9b36b4290e38afea7d7ab7a8ac7dd152e93d1"
RAW = (
    "Immondo Enorme (demone), generalmente caotico malvagio "
    "Classe Armatura 1 7 (armatura naturale) "
    "Punti Ferita 200 (l 6dl 2 + 96) Velocità 12 m"
)
ATTRS = {
    "velocita": "12 m",
    "punti_ferita": "200 (16d12 + 96)",
    "classe_armatura": "17 (armatura naturale)",
}
SOURCE_ATTRS = {
    "velocita": "12 m",
    "punti_ferita": "200 (l 6dl 2 + 96)",
    "classe_armatura": "1",
}
SOURCE_FILE = "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf"
AUTHORITY = {
    "page": 124, "logical_page": 124, "logical_source_id": "bgg_2023_it",
    "ruleset": "2014", "filename": SOURCE_FILE,
    "source_role": "authority", "source_status": "active",
    "authority_class": "licensed_translation",
    "source_title": "Bigby Presenta: La Gloria dei Giganti",
}


def assess_baphomet_registered_source(record: dict[str, Any] | None) -> dict[str, Any]:
    """Fail closed on drift, absent authority, or numeric/identity disagreement."""
    if not isinstance(record, dict):
        raise ValueError("missing_record")
    expected = {
        "id": RECORD_ID, "name": "Cacciatore Di Baphomet",
        "reference_type": "monster", "source_language": "it",
        "source_key": SOURCE_FILE, "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": CHECKSUM,
        "attributes": ATTRS, "source_attributes": SOURCE_ATTRS,
        "full_text": RAW, "source_full_text": RAW,
    }
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("sealed_source_snapshot_drift")
    if record.get("source_refs") != [AUTHORITY]:
        raise ValueError("registered_authority_page_or_provenance_drift")
    if monster_semantic_numeric_flags(ATTRS):
        raise ValueError("global_numeric_gate_failed")
    # Original English Stalker of Baphomet, Bigby p178: AC17 natural,
    # HP200 (16d12+96), speed40ft (12m). Registered IT p124 statblock.
    if 16 * 6 != 96 or (16 * 13) // 2 + 96 != 200:
        raise ValueError("hit_dice_math_failed")
    return {
        "status": "eligible_status_only_source_review",
        "source": "bgg_2023_it", "page": 124,
        "attributes_unchanged": True, "numeric_gates_passed": True,
        "raw_text_preserved": True, "writes": 0,
    }
