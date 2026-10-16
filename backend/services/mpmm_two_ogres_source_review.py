"""Read-only original-source review of two misclassified Ogre statblocks.

The same Italian PDF page 7 independently contains their two named, boxed
statblocks. Original source names begin with OCR digit '0', retained only in
source_name; display names will be corrected to capital-O Ogre after review.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

SOURCE = "Mostri del multiverso 201-294.pdf"
OWNER = "user_fabf28726a20"
TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
TARGETS = {
    "Ogre Bruto Con Catena": {
        "id": "ref_31d363e7eba9573c99a78bb56a5805f9",
        "original_name": "0Gre Bruto Con Catena",
        "checksum": "1082ee4b7f3570cf23ad4921aa961d8ff1bd2449ca648463205f2f95daba6a2e",
        "raw_sha": "80aa8cb0bf469429f27c3038b38ccbe74785578453330c4995a832d640b7691a",
        "flags": [],
        "attrs": {
            "classe_armatura": "11 (armatura di pelle)",
            "punti_ferita": "59 (7d10 + 21)",
            "velocita": "12 m",
        },
    },
    "Ogre Bunker": {
        "id": "ref_6a7601e7bf0158bea76adf2919f70b3e",
        "original_name": "0Gre Bunker",
        "checksum": "67aaad201bf066a2ede807b2695ac56b5c84b3e97551c8cd49fbc6df664f8128",
        "raw_sha": "6c7e65fb024f58f07bd687680232c7ebee0720a06b30ab8bc3d364a205aeac0c",
        "flags": ["sezione_potenzialmente_continua"],
        "attrs": {
            "classe_armatura": "15 (corazza, scudo)",
            "punti_ferita": "59 (7d10 + 21)",
            "velocita": "12 m",
        },
    },
}


def authority() -> dict[str, Any]:
    return {
        "page": 7, "ruleset": "2014", "filename": SOURCE,
        "source_role": "authority", "logical_page": 207,
        "source_title": TITLE, "source_status": "active",
        "authority_class": "licensed_translation",
        "logical_source_id": "mpmm_2022_it",
    }


def inspect_ogre(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    """Fail closed on any raw/source/numeric drift. No writes."""
    if name not in TARGETS or not isinstance(row, dict):
        raise ValueError("unknown_or_missing_original_ogre")
    t = TARGETS[name]
    before = {
        "id": t["id"],
        "user_id": OWNER,
        "name": t["original_name"],
        "normalized_name": t["original_name"].casefold(),
        "source_name": t["original_name"],
        "reference_type": "other",
        "review_status": "needs_review",
        "review_flags": t["flags"],
        "canonical_id": None,
        "source_key": SOURCE,
        "source_language": "it",
        "source_text_checksum": t["checksum"],
        "source_refs": [authority()],
        "review_corrections": {"_source_changed": True},
        "attributes": {},
        "source_attributes": {},
    }
    if any(row.get(key) != val for key, val in before.items()):
        raise ValueError("registered_ogre_snapshot_changed")
    raw = row.get("full_text")
    if not isinstance(raw, str) or raw != row.get("source_full_text"):
        raise ValueError("raw_description_drift")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != t["raw_sha"]:
        raise ValueError("source_raw_digest_changed")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(t["attrs"]):
        raise ValueError("semantic_identity_or_numeric_gate_failed")
    if (7 * (10 + 1)) // 2 + 21 != 59:
        raise ValueError("source_hit_dice_inconsistent")
    return {
        "status": "eligible_existing_ogre_monster_reclassification",
        "id": t["id"], "original_name": t["original_name"],
        "correct_name": name, "attributes": t["attrs"],
        "source_page": 207, "original_source_preserved": True,
        "historical_continuation_flag_to_be_resolved": bool(t["flags"]),
        "writes": 0,
    }
