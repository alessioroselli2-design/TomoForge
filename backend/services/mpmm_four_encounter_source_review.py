"""Read-only registered-source audit for four misclassified MPMM creatures.

All four are existing 'other/needs_review' rows with separately named Italian
monster stat blocks. This module performs no writes, forces no statuses, and
preserves the original registered narrative, OCR and provenance.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

SOURCE = "Mostri del multiverso 101-200.pdf"
USER = "user_fabf28726a20"
SOURCE_TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
TARGETS = {
    "Drow Capitano Di Casata": {
        "id": "ref_d960ed1c59e957b6a92f770e92f25bbf", "page": 2, "logical": 102,
        "checksum": "c168c5116948e541004c3dec607a09a22d2d31fd2aa947059f05253f4be87f1d",
        "raw_sha256": "2ba4e5766c50709db5c2699509b64dc99dfa7c51eb3efbba4c619b832f63d886",
        "attrs": {"classe_armatura": "16 (cotta di maglia)", "punti_ferita": "162 (25d8 + 50)", "velocita": "9 m"},
        "dice": (162, 25, 8, 50),
    },
    "Drow Consorte Prediletto": {
        "id": "ref_2eaf560c5b7d5de683f697706ba5b5b1", "page": 3, "logical": 103,
        "checksum": "843b6ecb2efc83a1664f175911aee9a0b75c4eb40934b82c7610596a2891faec",
        "raw_sha256": "cd1ed951fb38f162abda784b2c34d4c0ed02b02c16e41ce3577ed832cb53a8de",
        "attrs": {"classe_armatura": "15 (18 con armatura magica)", "punti_ferita": "240 (32d8 + 96)", "velocita": "9 m"},
        "dice": (240, 32, 8, 96),
    },
    "Drow Lama D'Ombra": {
        "id": "ref_b0d0722d99325afda0796bdac0e33313", "page": 5, "logical": 105,
        "checksum": "0667001843a7666b22a95e76f4cb468f2ec93275a79692ffb441da49a0727307",
        "raw_sha256": "a7b174d0a09beba60888e84d78303902cca1ef2bd0257822e3e7b3bb4405a28e",
        "attrs": {"classe_armatura": "17 (cuoio borchiato)", "punti_ferita": "150 (20d8 + 60)", "velocita": "9 m"},
        "dice": (150, 20, 8, 60),
    },
    "Giff": {
        "id": "ref_4b8a96fad653555cb3edc25dcc4a8b3b", "page": 31, "logical": 131,
        "checksum": "087f95a54f9dc5b83034ef4f803be470692cef04cf680b86b56a2d6031446312",
        "raw_sha256": "73839b1586099c5f117109e05ab1c6f7899c68b3c4ae44fad35e8940b394a999",
        "attrs": {"classe_armatura": "16 (corazza)", "punti_ferita": "60 (8d8 + 24)", "velocita": "9 m"},
        "dice": (60, 8, 8, 24),
    },
}


def authority(page: int, logical: int) -> dict[str, Any]:
    return {
        "page": page, "ruleset": "2014", "filename": SOURCE,
        "source_role": "authority", "logical_page": logical,
        "source_title": SOURCE_TITLE, "source_status": "active",
        "authority_class": "licensed_translation",
        "logical_source_id": "mpmm_2022_it",
    }


def assess_mpmm_existing_creature(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    """Independently validate one exact original registered record."""
    if name not in TARGETS or not isinstance(row, dict):
        raise ValueError("target_missing_or_unregistered")
    t = TARGETS[name]
    expected = {
        "id": t["id"], "user_id": USER,
        "name": name, "source_name": name,
        "normalized_name": name.casefold().replace("'", " "),
        "reference_type": "other", "review_status": "needs_review",
        "review_flags": [], "canonical_id": None,
        "source_key": SOURCE, "source_language": "it",
        "source_text_checksum": t["checksum"],
        "review_corrections": {"_source_changed": True},
        "source_refs": [authority(t["page"], t["logical"])],
        "attributes": {}, "source_attributes": {},
    }
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("registered_original_row_changed")
    raw = row.get("source_full_text")
    if not isinstance(raw, str) or raw != row.get("full_text"):
        raise ValueError("raw_original_not_preserved")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != t["raw_sha256"]:
        raise ValueError("original_raw_sha256_drift")
    if monster_semantic_numeric_flags(t["attrs"]):
        raise ValueError("strict_global_numeric_semantic_gate_failed")
    hp, n, sides, bonus = t["dice"]
    if (n * (sides + 1)) // 2 + bonus != hp:
        raise ValueError("hit_dice_average_incoherent")
    return {
        "status": "eligible_existing_source_reclassification",
        "name": name, "record_id": t["id"],
        "logical_page": t["logical"],
        "proposed_attributes": t["attrs"],
        "source_immutable": True, "writes": 0,
    }
