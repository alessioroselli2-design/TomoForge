"""Read-only, source-locked adjudication for Bigby IT Gegant.

Retain the Italian source OCR verbatim. This independent registered-source
review is distinct from the inconclusive protected OCR pull request #428.
"""

from __future__ import annotations

from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_7a30c2cd8ab25a578d7d6f02b0877061"
CHECKSUM = "f7dab83b6e1f56c1547cd805bbed080837f8b4637b06c269ea235b9421cd5b75"
SOURCE_FILE = "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf"
RAW = (
    "Mostruosità Mastodontica, senza allineamento "
    "Classe Armatura 17 (armatura naturale) "
    "Punti Ferita 325 (2l d20 + 1 05) "
    "Velocità 15 m, scavare 15 m, volare 24 m"
)
ATTRS = {
    "classe_armatura": "17 (armatura naturale)",
    "punti_ferita": "325 (21d20 + 105)",
    "velocita": "15 m, scavare 15 m, volare 24 m",
}
SOURCE_ATTRS = {
    "classe_armatura": "17 (armatura naturale)",
    "punti_ferita": "325 (2l d20 + 1 05)",
    "velocita": "15 m, scavare 15 m, volare 24 m",
}
AUTHORITY = {
    "page": 142,
    "logical_page": 142,
    "logical_source_id": "bgg_2023_it",
    "ruleset": "2014",
    "filename": SOURCE_FILE,
    "source_role": "authority",
    "source_status": "active",
    "authority_class": "licensed_translation",
    "source_title": "Bigby Presenta: La Gloria dei Giganti",
}


def assess_gegant_registered_source(record: dict[str, Any] | None) -> dict[str, Any]:
    """Fail closed unless the original record and independent numeric proof agree."""
    if not isinstance(record, dict):
        raise ValueError("missing_record")

    expected = {
        "id": RECORD_ID,
        "name": "Gegant",
        "source_name": "Gegant",
        "reference_type": "monster",
        "source_language": "it",
        "source_key": SOURCE_FILE,
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": CHECKSUM,
        "attributes": ATTRS,
        "source_attributes": SOURCE_ATTRS,
        "full_text": RAW,
        "source_full_text": RAW,
        "review_corrections": {"_source_changed": True},
    }
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("sealed_source_snapshot_drift")
    if record.get("source_refs") != [AUTHORITY]:
        raise ValueError("registered_authority_page_or_provenance_drift")
    if monster_semantic_numeric_flags(ATTRS):
        raise ValueError("global_numeric_gate_failed")

    # Gigant (not a generic giant), original Bigby Presents English p154:
    # Gargantuan monstrosity; AC17; HP325(21d20+105); 50ft,
    # burrow50ft, fly80ft. Constitution 21 (+5) yields 21*5=105.
    if 21 * 5 != 105 or (21 * 21) // 2 + 105 != 325:
        raise ValueError("hit_dice_math_failed")
    return {
        "status": "eligible_status_only_source_review",
        "source": "bgg_2023_it",
        "page": 142,
        "original_english_page": 154,
        "attributes_unchanged": True,
        "numeric_gates_passed": True,
        "raw_text_preserved": True,
        "writes": 0,
    }
