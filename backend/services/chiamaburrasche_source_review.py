"""Fail-closed exact source review: Chiamaburrasche, Bigby IT p154.

The stored Italian raw OCR has split dice glyphs "27d l 2 + 1 35".
The preserved operational attributes match the independently sourced
Storm Giant Tempest Caller statblock in the English Bigby original.
No ordinary OCR gates are relaxed; this reader never writes records.
"""

from __future__ import annotations

from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_e075432f79145e36a484fb6ce88eb62a"
SOURCE_CHECKSUM = "411c45449c2b747462e5fa62b10a032a1d9672248d0c5a5b77b85ff2678fce17"
ITALIAN_RAW = (
    "Gigante Enorme (stregone), qualsiasi allineamento "
    "Classe Armatura 17 (armatura naturale) "
    "Punti Ferita 310 (27d l 2 + 1 35) "
    "Velocità 15 m , volare 15 m (fluttuare), nuotare 15 m"
)
ATTRIBUTES = {
    "classe_armatura": "17 (armatura naturale)",
    "punti_ferita": "310 (27d12 + 135)",
    "velocita": "15 m, volare 15 m (fluttuare), nuotare 15 m",
}


def assess_chiamaburrasche_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Return eligibility only for the original exact pending Italian record."""
    if not isinstance(record, dict):
        raise ValueError("missing_registered_record")
    if not all(
        (
            record.get("id") == RECORD_ID,
            record.get("name") == "Chiamaburrasche",
            record.get("reference_type") == "monster",
            record.get("review_status") == "pending",
            record.get("canonical_id") is None,
            record.get("review_flags") == [
                "ocr_da_verificare",
                "source_guided_repair",
            ],
            record.get("source_text_checksum") == SOURCE_CHECKSUM,
            record.get("attributes") == ATTRIBUTES,
            record.get("full_text") == ITALIAN_RAW,
        )
    ):
        raise ValueError("registered_snapshot_drift")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1:
        raise ValueError("authority_source_count_drift")
    ref = refs[0]
    if not isinstance(ref, dict) or not all(
        (
            ref.get("page") == 154,
            ref.get("logical_page") == 154,
            ref.get("logical_source_id") == "bgg_2023_it",
            ref.get("source_status") == "active",
            ref.get("source_role") == "authority",
            ref.get("authority_class") == "licensed_translation",
            ref.get("filename")
            == "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf",
            ref.get("source_title") == "Bigby Presenta: La Gloria dei Giganti",
            ref.get("ruleset") == "2014",
        )
    ):
        raise ValueError("registered_authority_drift")
    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("global_numeric_gates_failed")
    if (27 * (12 + 1)) // 2 + 135 != 310 or 27 * 5 != 135:
        raise ValueError("hit_point_dice_disagreement")
    # Independently corroborated English original Bigby p182:
    # Storm Giant Tempest Caller Huge Giant (sorcerer), AC17 natural armor,
    # HP310 (27d12+135), Speed 50ft, fly50ft hover, swim50ft.
    return {
        "status": "eligible_status_only_source_review",
        "source_id": "bgg_2023_it",
        "registered_pages": [154],
        "attributes_unchanged": True,
        "raw_dice_text_preserved": True,
        "numeric_gates_passed": True,
        "snapshot_unchanged": True,
        "separate_editorial_adjudication_required": True,
    }
