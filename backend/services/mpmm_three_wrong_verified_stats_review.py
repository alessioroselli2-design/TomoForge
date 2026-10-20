"""Fail-closed read-only re-audit for three incorrectly 'verified' MPMM stats.

Existing monster/verified status alone does not establish numeric correctness.
These records inadvertently inherited CA/HP/speed from an adjacent distinct
creature on the very same original Italian source page. No writes here.
"""
from __future__ import annotations

import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

OWNER = "user_fabf28726a20"
TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
SOURCE_ID = "mpmm_2022_it"

TARGETS = {
    "Neogi": {
        "id": "ref_de25807ecb645c0d810a35e557b9e37b",
        "file": "Mostri del multiverso 101-200.pdf", "pages": (99, 100),
        "logical_pages": (199, 200),
        "checksum": "63c346ef9699e010716f86b180a84ae4e5f56eb70ecf41422cb72e150198d60b",
        "sha256": "01595c6d7e8803d6f9c5a3dbec1e22af1f9991f11f60b95e2c7c0f9645ea4ce8",
        "original_attrs": {"classe_armatura":"11", "punti_ferita":"7 (3d4)", "velocita":"6 m, scalare 6m"},
        "source_attrs": {"classe_armatura":"1","punti_ferita":"33 (6d6 + 12)","velocita":"9 m, scalare 9 m"},
        "fixed_attrs": {"classe_armatura":"15 (armatura naturale)","punti_ferita":"33 (6d6 + 12)","velocita":"9 m, scalare 9 m"},
        "dice": (33, 6, 6, 12),
        "neighbor": "Cucciolo Di Neogi",
    },
    "Tortuga": {
        "id": "ref_d33a3518db9a58a281114a7bce5e7396",
        "file": "Mostri del multiverso 201-294.pdf", "pages": (58,),
        "logical_pages": (258,),
        "checksum": "50e6f389e5fda4a1c0e756f9e7b6c7bf4d93cd3799b8801ee77f1398000bcdfa",
        "sha256": "0037d270ebef8790b35cdc4f3248de39595448a796ec9c1ce7943ed7349c3413",
        "original_attrs": {"classe_armatura":"17 (armatura naturale)","punti_ferita":"33 (6d8 + 6)","velocita":"9 m"},
        "source_attrs": {"classe_armatura":"17 (armatura naturale)","punti_ferita":"22 (4d8 + 4)","velocita":"9 m"},
        "fixed_attrs": {"classe_armatura":"17 (armatura naturale)","punti_ferita":"22 (4d8 + 4)","velocita":"9 m"},
        "dice": (22, 4, 8, 4),
        "neighbor": "Tortuga Druido",
    },
    "Xvart Warlock Di Raxivort": {
        "id": "ref_a039088ef69452beaaedb512ab702231",
        "file": "Mostri del multiverso 201-294.pdf", "pages": (71,),
        "logical_pages": (271,),
        "checksum": "5b0618f783ff5ef409059e0bb78ad5977dd13453d7d7125f68c084f3a4be5366",
        "sha256": "ac3465e50e88e51dca7d91c42a60612caf959de8a9355018058da1c57f153fe3",
        "original_attrs": {"classe_armatura":"13 (armatura di cuoio)","punti_ferita":"7 (2d6)","velocita":"9 m"},
        "source_attrs": {"classe_armatura":"1","punti_ferita":"22 (5d6 + 5)","velocita":"9 m"},
        "fixed_attrs": {"classe_armatura":"12 (15 con armatura magica)","punti_ferita":"22 (5d6 + 5)","velocita":"9 m"},
        "dice": (22, 5, 6, 5),
        "neighbor": "Xvart",
    },
}


def authority(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the exact previously registered authority pages, in order."""
    return [
        {
            "page": page, "ruleset": "2014", "filename": spec["file"],
            "source_role": "authority", "logical_page": logical,
            "source_title": TITLE, "source_status": "active",
            "authority_class": "licensed_translation",
            "logical_source_id": SOURCE_ID,
        }
        for page, logical in zip(spec["pages"], spec["logical_pages"], strict=True)
    ]


def review_misattributed_stats(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    """Guard against overwriting any changed, untracked, or different source."""
    if name not in TARGETS or not isinstance(row, dict):
        raise ValueError("missing_registered_monster")
    spec = TARGETS[name]
    required = {
        "id": spec["id"], "user_id": OWNER, "name": name,
        "source_name": name, "normalized_name": name.casefold(),
        "reference_type": "monster", "review_status": "verified",
        "review_flags": [], "canonical_id": None,
        "source_key": spec["file"], "source_language": "it",
        "source_text_checksum": spec["checksum"],
        "attributes": spec["original_attrs"],
        "source_attributes": spec["source_attrs"],
        "review_corrections": {"_source_changed": True},
        "source_refs": authority(spec),
    }
    if any(row.get(k) != v for k, v in required.items()):
        raise ValueError("original_verified_snapshot_drift")
    full = row.get("full_text")
    if not isinstance(full, str) or full != row.get("source_full_text"):
        raise ValueError("historical_raw_text_changed")
    if hashlib.sha256(full.encode("utf-8")).hexdigest() != spec["sha256"]:
        raise ValueError("original_source_sha256_mismatch")
    hp, count, sides, bonus = spec["dice"]
    if (count * (sides + 1)) // 2 + bonus != hp:
        raise ValueError("wrong_original_hit_dice_average")
    if monster_semantic_numeric_flags(spec["fixed_attrs"]):
        raise ValueError("original_global_semantic_numeric_gate_failed")
    return {
        "status": "eligible_exact_statblock_correction",
        "name": name, "id": spec["id"],
        "already_verified_but_wrong": True,
        "neighbor_not_the_same_monster": spec["neighbor"],
        "correct_source_fields_preserved": True,
        "correct_attributes": spec["fixed_attrs"],
        "writes": 0,
    }
