"""Fail-closed source-review for Bigby Italian Nuvola Spettrale (Spectral Cloud).

No writes; no changes to original source text or global math/OCR gates.
"""
from __future__ import annotations
from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_f1d7b2c1ee66563587537988b9399a29"
SOURCE_CHECKSUM = "fe5cf0e24b2637181dd7f3db13a2fb484d80f1bf79452e4a26ca1a6794cc6c5a"
ITALIAN_RAW = (
    "Non morto Enorme, generalmente neutrale Classe Armatura 1 1 "
    "Punti Ferita 1 89 (18dl2 + 72) "
    "Velocità O m, volare 12 m (fluttuare)"
)
ATTRIBUTES = {
    "classe_armatura": "11",
    "punti_ferita": "189 (18d12 + 72)",
    "velocita": "0 m, volare 12 m (fluttuare)",
}


def assess_nuvola_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Only exact registered authority and original statistical fields qualify."""
    if not isinstance(record, dict) or not all((
        record.get("id") == RECORD_ID,
        record.get("name") == "Nuvola Spettrale",
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
        ref.get("page") == 168,
        ref.get("logical_page") == 168,
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
    # Independently corroborated English Spectral Cloud, Bigby original p176:
    # AC11, HP189 (18d12+72), speed 0 ft, fly40 ft hover (12m).
    if 18 * 4 != 72 or (18 * (12 + 1)) // 2 + 72 != 189:
        raise ValueError("hit_dice_math_failed")
    return {
        "status": "eligible_status_only_source_review",
        "source": "bgg_2023_it",
        "page": 168,
        "attributes_unchanged": True,
        "numeric_gates_passed": True,
        "raw_text_preserved": True,
    }
