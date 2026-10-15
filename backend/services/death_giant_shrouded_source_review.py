"""Read-only adjudication of the Bigby Death Giant Shrouded One source split.

The registered page 156 contains the descriptive text, while the stat block
belongs to PDF page 155. Never fabricate missing OCR source_attributes.
"""

from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_efc0ad0100b750f6a96e4e221e47b897"
SOURCE_FILE = "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf"
SOURCE_CHECKSUM = "b78e2d2d9a54597a0bd3f1c0869c2f4f5b9ff7c9229f7ca868ccfb622382aa92"
RAW_SHA256 = "714da397ccfc8091094896b6fec9396b93e3c2c4df250a94af00f455ac780597"
DESCRIPTION_PAGE = 156
STATBLOCK_PAGE = 155
ATTRS = {
    "classe_armatura": "12 (15 con armatura magica)",
    "punti_ferita": "195 (17d12 + 85)",
    "velocita": "12 m",
}
AUTHORITY = {
    "page": DESCRIPTION_PAGE,
    "logical_page": DESCRIPTION_PAGE,
    "logical_source_id": "bgg_2023_it",
    "ruleset": "2014",
    "filename": SOURCE_FILE,
    "source_role": "authority",
    "source_status": "active",
    "authority_class": "licensed_translation",
    "source_title": "Bigby Presenta: La Gloria dei Giganti",
}


def assess_death_giant_shrouded_registered_source(
    record: dict[str, Any] | None,
) -> dict[str, Any]:
    """Fail closed on drift; page 155 must be recorded before verification."""
    if not isinstance(record, dict):
        raise ValueError("missing_record")
    expected = {
        "id": RECORD_ID,
        "name": "Gigante Della Morte Ammantato",
        "source_name": "Gigante Della Morte Ammantato",
        "reference_type": "monster",
        "source_language": "it",
        "source_key": SOURCE_FILE,
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": ATTRS,
        "source_attributes": {},
        "review_corrections": {},
    }
    if any(record.get(k) != v for k, v in expected.items()):
        raise ValueError("registered_source_snapshot_drift")
    if record.get("source_refs") != [AUTHORITY]:
        raise ValueError("registered_description_page_drift")

    raw = record.get("source_full_text")
    if not isinstance(raw, str) or record.get("full_text") != raw:
        raise ValueError("source_raw_mismatch")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != RAW_SHA256:
        raise ValueError("registered_description_raw_hash_drift")
    if monster_semantic_numeric_flags(ATTRS):
        raise ValueError("global_numeric_gate_failed")

    # Visual primary source IT PDF p155: same-name local stat block AC12
    # (15 with mage armor), HP195(17d12+85), speed12m, CON20 (+5).
    # English Death Giant Shrouded One (Bigby p127) also corroborates.
    if 17 * 5 != 85 or (17 * 13) // 2 + 85 != 195:
        raise ValueError("hit_dice_math_failed")
    return {
        "status": "eligible_source_relink_and_status_review",
        "original_description_page": DESCRIPTION_PAGE,
        "required_statblock_page": STATBLOCK_PAGE,
        "source": "bgg_2023_it",
        "operational_attributes_preserved": True,
        "source_attributes_preserved": True,
        "raw_text_preserved": True,
        "numeric_gates_passed": True,
        "writes": 0,
    }
