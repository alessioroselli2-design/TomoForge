"""Fail-closed registered-source reviews for three MPMM encounter creatures.

Original Italian source statblocks independently read at PDF pages 2, 60, 61
in the 201-294 segment. No database writes and no historical OCR promotion.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

SOURCE = "Mostri del multiverso 201-294.pdf"
USER = "user_fabf28726a20"
TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
TARGETS = {
    "Nilbog": {
        "id": "ref_74f421397e0656eebe23db01ed73c54d",
        "page": 2, "logical_page": 202,
        "checksum": "6bc877772d395f186160f56c72d934ae3fb150d02ac5258369b8ed5ebe818a80",
        "raw_sha256": "92bbfb3148d742eda44283d1c9bb61dbceb10aaa97a65e5c6f2fff3df08d0a36",
        "attrs": {
            "classe_armatura": "13 (armatura di cuoio)",
            "punti_ferita": "7 (2d6)",
            "velocita": "9 m",
        },
        "dice": (7, 2, 6, 0),
    },
    "Troll Putrefatto": {
        "id": "ref_f8190d4e510b551fb2858dda3ffb6727",
        "page": 60, "logical_page": 260,
        "checksum": "46f0854ede0eedc87d86bb06e548575311f4560d09003150f2d64ba7d03b05ee",
        "raw_sha256": "c7032c854c36d70f4414ef6777bbefa104af0c03acd3bfdc9d4799b9bce3c34c",
        "attrs": {
            "classe_armatura": "16 (armatura naturale)",
            "punti_ferita": "138 (12d10 + 72)",
            "velocita": "9 m",
        },
        "dice": (138, 12, 10, 72),
    },
    "Troll Velenoso": {
        "id": "ref_59cd301c125855b9935f588acf0319dc",
        "page": 61, "logical_page": 261,
        "checksum": "3d3b3ef3be899dc59e67c0db990682e45f9a8adb5f57eedb4bd49bd273226d4d",
        "raw_sha256": "a048fb588b6fb66eabc31af377548a4ac2eea9439b9346cfad01fde8945c5efc",
        "attrs": {
            "classe_armatura": "15 (armatura naturale)",
            "punti_ferita": "94 (9d10 + 45)",
            "velocita": "9 m",
        },
        "dice": (94, 9, 10, 45),
    },
}


def authority(page: int, logical_page: int) -> dict[str, Any]:
    """Return precisely the registered licensed translation authority."""
    return {
        "page": page,
        "ruleset": "2014",
        "filename": SOURCE,
        "source_role": "authority",
        "logical_page": logical_page,
        "source_title": TITLE,
        "source_status": "active",
        "authority_class": "licensed_translation",
        "logical_source_id": "mpmm_2022_it",
    }


def inspect_existing_creature(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    """Require exact identity, historical source snapshot and dice checks."""
    if name not in TARGETS or not isinstance(row, dict):
        raise ValueError("registered_candidate_missing")
    spec = TARGETS[name]
    expected = {
        "id": spec["id"],
        "user_id": USER,
        "name": name,
        "source_name": name,
        "normalized_name": name.casefold(),
        "reference_type": "other",
        "review_status": "needs_review",
        "review_flags": [],
        "canonical_id": None,
        "source_language": "it",
        "source_key": SOURCE,
        "source_text_checksum": spec["checksum"],
        "attributes": {},
        "source_attributes": {},
        "review_corrections": {"_source_changed": True},
        "source_refs": [authority(spec["page"], spec["logical_page"])],
    }
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("registered_original_source_snapshot_drift")
    raw = row.get("source_full_text")
    if not isinstance(raw, str) or row.get("full_text") != raw:
        raise ValueError("historical_description_modified")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != spec["raw_sha256"]:
        raise ValueError("historical_description_sha256_drift")
    hp, n, faces, bonus = spec["dice"]
    if (n * (faces + 1)) // 2 + bonus != hp:
        raise ValueError("original_statblock_dice_average_mismatch")
    if monster_semantic_numeric_flags(spec["attrs"]):
        raise ValueError("unmodified_global_numeric_gate_failed")
    return {
        "name": name,
        "id": spec["id"],
        "status": "eligible_original_source_reclassification",
        "page": spec["logical_page"],
        "attributes": spec["attrs"],
        "raw_preserved": True,
        "writes": 0,
    }
