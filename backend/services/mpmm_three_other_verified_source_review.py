"""Read-only original Italian MPMM audit of three *other/verified* creature rows.

'Verified' is historical review of a wrongly classified reference, NOT a verified
monster. Each original source page contains a separate complete named statblock.
No writes, no duplicate creations and no historical text changes in this audit.
"""
from __future__ import annotations

import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER = "user_fabf28726a20"
SOURCE = "Mostri del multiverso 201-294.pdf"
SOURCE_TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
TARGETS = {
    "Signore Della Guerra": {
        "id": "ref_c42688ba9a4f5ebdafa48fc590e3fe3d",
        "page": 46,
        "checksum": "6603804eb368e3e362c755e70617a8220ae72ccaf7d6abc6115fe49fbd761f82",
        "raw_sha": "65dd691224f657777502c484b208ea8dae7d951cc39e1c6a50e8cbf4bc404007",
        "attrs": {"classe_armatura": "18 (piastre)", "punti_ferita": "229 (27d8 + 108)", "velocita": "9 m"},
        "dice": (229, 27, 8, 108),
    },
    "Strangolatore": {
        "id": "ref_bfe7f004f1425c7385179f2564e53123",
        "page": 49,
        "checksum": "7b11b01ca65ad756e0fcc8821362c27d36ba23f3896f65f569c9afa383190483",
        "raw_sha": "c07e216b04fdf0326dc8af6bdd1a727f1eae7a8dc09061847ea0333b2d004792",
        "attrs": {"classe_armatura": "16 (armatura naturale)", "punti_ferita": "13 (3d6 + 3)", "velocita": "9 m"},
        "dice": (13, 3, 6, 3),
    },
    "Ululatore": {
        "id": "ref_1e06eec870235fe5b649829b9be6b69c",
        "page": 63,
        "checksum": "f4f9be0f69fc747f7a99a4889e6dc3b84ebaa16bbfd53179bbb840f7af0ff90b",
        "raw_sha": "f9291d0533e49ae290999dc36a8f1f7b38e239e5c54180ad55334bbfdb1606fb",
        "attrs": {"classe_armatura": "16 (armatura naturale)", "punti_ferita": "90 (12d10 + 24)", "velocita": "12 m"},
        "dice": (90, 12, 10, 24),
    },
}


def authority(page: int) -> dict[str, Any]:
    return {
        "page": page, "ruleset": "2014", "filename": SOURCE,
        "source_role": "authority", "logical_page": 200 + page,
        "source_title": SOURCE_TITLE, "source_status": "active",
        "authority_class": "licensed_translation",
        "logical_source_id": "mpmm_2022_it",
    }


def review_existing_creature(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    """Fail-closed gate including exact source snapshot and mathematical HP."""
    if name not in TARGETS or not isinstance(row, dict):
        raise ValueError("unregistered_creature_or_original_missing")
    spec = TARGETS[name]
    expected = {
        "id": spec["id"], "user_id": OWNER,
        "name": name, "source_name": name, "normalized_name": name.casefold(),
        "reference_type": "other", "review_status": "verified",
        "review_flags": [], "canonical_id": None,
        "source_key": SOURCE, "source_language": "it",
        "source_text_checksum": spec["checksum"],
        "source_refs": [authority(spec["page"])],
        "attributes": {}, "source_attributes": {}, "review_corrections": {},
    }
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("original_source_or_historical_review_drift")
    raw = row.get("full_text")
    if not isinstance(raw, str) or raw != row.get("source_full_text"):
        raise ValueError("original_narrative_changed")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != spec["raw_sha"]:
        raise ValueError("original_raw_sha256_changed")
    hp, count, die, bonus = spec["dice"]
    if count * (die + 1) // 2 + bonus != hp:
        raise ValueError("original_hit_dice_average_inconsistent")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(spec["attrs"]):
        raise ValueError("strict_global_identity_or_numeric_gate_failed")
    return {
        "status": "eligible_original_creature_reclassification",
        "name": name, "id": spec["id"],
        "logical_page": 200 + spec["page"], "attributes": spec["attrs"],
        "historically_verified_as_other_only": True,
        "raw_original_preserved": True, "writes": 0,
    }
