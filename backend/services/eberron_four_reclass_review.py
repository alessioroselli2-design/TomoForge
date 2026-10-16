"""Fail-closed exact source reviews for four existing misclassified Eberron monsters.

Eberron Italian PDF was directly inspected: same-name boxed stat blocks, never
adjacent unrelated values. This module reads records but performs no writes.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

SOURCE = "618795464-Eberron.pdf"
USER_ID = "user_fabf28726a20"
TITLE = "Eberron: Rinascita dopo l’Ultima Guerra"
SPECS = {
    "Corridore": {
        "id": "ref_8f2a5c4786b95df2bf4dbeb8462b1288",
        "page": 292, "statpage": 292, "status": "verified", "corrections": {},
        "checksum": "b83f10785fea95396486c6f0f2a8e2456b1bcf4fef4573e15eb35da1ece948b9",
        "raw_hash": "8d947d3ea02ec468d182f3bae73b625aa659c84e56291b634a58f27ab2ec046e",
        "attrs": {"classe_armatura": "14", "punti_ferita": "9 (2d8)", "velocita": "15 m"},
        "dice": (9, 2, 8, 0),
    },
    "Dolgaunt": {
        "id": "ref_2f8a6bc3d49b510f9b04fe5f414d1abc",
        "page": 293, "statpage": 293, "status": "verified", "corrections": {},
        "checksum": "39b8f59ef3130e83d26baceac2bcf07cc9216efaba65f286e3d0152bd35042f9",
        "raw_hash": "8dabd2f64a29f8c816a4da8a41eb4bce6ae0fe4774d20d5755f59596ab485517",
        "attrs": {"classe_armatura": "16 (Difesa Senza Armatura)", "punti_ferita": "33 (6d8 + 6)", "velocita": "12 m"},
        "dice": (33, 6, 8, 6),
    },
    "Mordakhesh": {
        "id": "ref_0868e1924b1a5417ba0ee221f25069ae",
        "page": 306, "statpage": 306, "status": "needs_review",
        "corrections": {"_source_changed": True},
        "checksum": "8fdf448a5b52a3c7ff920de9c78894fa835ec2c9c92453a786cb1ba476cefa98",
        "raw_hash": "0dc982962e82ebff4b3159488f51d1d3457da7ba3137d82418198d4741bde430",
        "attrs": {"classe_armatura": "18 (armatura completa)", "punti_ferita": "170 (20d8 + 80)", "velocita": "12 m"},
        "dice": (170, 20, 8, 80),
    },
    "Sul Khatesh": {
        "id": "ref_6a85d321c3a25bfba7d633377b0fccf0",
        "page": 314, "statpage": 315, "status": "verified", "corrections": {},
        "checksum": "77ee5df17eab19b26f2e8cda25814e61c9c1c82f5531ddb3c82f691d94ea7486",
        "raw_hash": "0841402170e004d2b0b7fd3370cb116a4ea423a50c4c2848ab1f857c60a45dec",
        "attrs": {"classe_armatura": "22 (armatura naturale)",
                  "punti_ferita": "475 (50d10 + 200)",
                  "velocita": "12 m, volare 12 m (fluttuare)"},
        "dice": (475, 50, 10, 200),
    },
}


def authority(page: int) -> dict[str, Any]:
    return {
        "page": page, "ruleset": "2014", "filename": SOURCE,
        "source_role": "authority", "logical_page": page,
        "source_title": TITLE, "source_status": "active",
        "authority_class": "licensed_translation",
        "logical_source_id": "erlw_2019_it",
    }


def assess_original_eberron_monster(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    """Individually check exact registered source, unmodified raw and numerical math."""
    if name not in SPECS or not isinstance(row, dict):
        raise ValueError("invalid_target")
    spec = SPECS[name]
    expected = {
        "id": spec["id"], "user_id": USER_ID,
        "name": name, "source_name": name,
        "normalized_name": name.casefold(),
        "reference_type": "other", "review_status": spec["status"],
        "review_flags": [], "canonical_id": None,
        "source_language": "it", "source_key": SOURCE,
        "attributes": {}, "source_attributes": {},
        "review_corrections": spec["corrections"],
        "source_text_checksum": spec["checksum"],
        "source_refs": [authority(spec["page"])],
    }
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("sealed_original_source_drift")
    raw = row.get("source_full_text")
    if not isinstance(raw, str) or row.get("full_text") != raw:
        raise ValueError("source_text_pair_mismatch")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != spec["raw_hash"]:
        raise ValueError("original_text_sha256_mismatch")
    if not raw.strip():
        raise ValueError("original_source_description_missing")
    hp, count, faces, bonus = spec["dice"]
    if count * (faces + 1) // 2 + bonus != hp:
        raise ValueError("original_statblock_hit_dice_average_incoherent")
    if monster_semantic_numeric_flags(spec["attrs"]):
        raise ValueError("original_statblock_numeric_gate_failed")
    refs = [authority(spec["page"])]
    if spec["statpage"] != spec["page"]:
        refs.append(authority(spec["statpage"]))
    return {
        "name": name, "status": "eligible_original_source_reclassification",
        "record_id": spec["id"],
        "old_type": "other", "proposed_type": "monster",
        "proposed_attributes": spec["attrs"],
        "original_narrative_page": spec["page"],
        "named_statblock_page": spec["statpage"],
        "proposed_refs": refs,
        "original_raw_preserved": True, "source_attributes_preserved": True,
        "writes": 0,
    }
