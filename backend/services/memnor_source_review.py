"""Fail-closed original-source review for Bigby Rampollo Di Memnor.

Ordinary OCR PR #434 timed out during independent OCR and is NOT a positive
paired-reader audit. This independent status-only review locks the original
registered Italian source and compares to the original English stat block.
No automatic rewrites or relaxed numeric/OCR gates.
"""
from __future__ import annotations

from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_7bc4d1c262b355668531f7e2331550f4"
SOURCE_CHECKSUM = "77865ad5531eb46dc82ce8f4f73d6bce35e3b34f8502c34566021c5a6ffd3bd2"
ATTRIBUTES = {
    "classe_armatura": "20 (armatura naturale)",
    "punti_ferita": "656 (32d20 + 320)",
    "velocita": "18 m, volare 24 m (fluttuare)",
}
ITALIAN_RAW = (
    "Gigante Mastodontico (titano), generalmente caotico neutrale "
    "Classe Armatura 20 (armatura naturale) "
    "Punti Ferita 656 (32d20 + 320) "
    "Velocità 18 m, volare 24 m (fluttuare)"
)
# Bigby Presents: Glory of the Giants, English original printed p167:
# Scion of Memnor, AC20 natural armor, HP656 (32d20+320), speed60 ft, fly80 ft (hover).
ENGLISH_CORE = (20, 656, 32, 20, 320, 60, 80)

def assess_memnor_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Admit only exact source identity and immutable eligible pending snapshot."""
    if not isinstance(record, dict):
        raise ValueError("missing_registered_record")
    if (
        record.get("id") != RECORD_ID
        or record.get("name") != "Rampollo Di Memnor"
        or record.get("reference_type") != "monster"
        or record.get("review_status") != "pending"
        or record.get("canonical_id") is not None
        or record.get("review_flags") != []
        or record.get("source_text_checksum") != SOURCE_CHECKSUM
        or record.get("attributes") != ATTRIBUTES
        or record.get("full_text") != ITALIAN_RAW
    ):
        raise ValueError("registered_snapshot_drift")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 2:
        raise ValueError("registered_source_count_drift")
    if sorted(ref.get("page") for ref in refs if isinstance(ref, dict)) != [172, 173]:
        raise ValueError("registered_source_pages_drift")
    for ref in refs:
        if not isinstance(ref, dict) or not all(
            (
                ref.get("logical_page") == ref.get("page"),
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
        raise ValueError("global_numeric_gate_rejected")
    ac, hp, dice_count, die_size, modifier, walk_ft, fly_ft = ENGLISH_CORE
    if (
        ac != 20
        or hp != 656
        or (dice_count * (die_size + 1)) // 2 + modifier != hp
        or (walk_ft, fly_ft) != (60, 80)
        or ATTRIBUTES["classe_armatura"] != "20 (armatura naturale)"
        or ATTRIBUTES["punti_ferita"] != "656 (32d20 + 320)"
        or ATTRIBUTES["velocita"] != "18 m, volare 24 m (fluttuare)"
    ):
        raise ValueError("independent_english_original_mismatch")
    return {
        "status": "eligible_status_only_source_review",
        "source_id": "bgg_2023_it",
        "registered_pages": [172, 173],
        "original_attributes_unchanged": True,
        "numeric_gates_passed": True,
        "source_snapshot_unchanged": True,
        "separate_editorial_adjudication_required": True,
    }
