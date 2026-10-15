"""Fail-closed original-source audit of four misclassified Eberron monsters.

No writes. All four already have registered Italian PDF narratives/identities,
but were typed 'other' and lack numeric monster attributes. Separate source
pages and historical OCR are immutable; only a separately guarded SQL review
may reclassify each existing ID, never create a duplicate.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

SOURCE = "618795464-Eberron.pdf"
OWNER = "user_fabf28726a20"
TITLE = "Eberron: Rinascita dopo l’Ultima Guerra"
TARGETS = {
    "Corridore": {
        "id": "ref_8f2a5c4786b95df2bf4dbeb8462b1288",
        "page": 292, "stat_page": 292,
        "status": "verified", "corrections": {},
        "checksum": "b83f10785fea95396486c6f0f2a8e2456b1bcf4fef4573e15eb35da1ece948b9",
        "hash": "8d947d3ea02ec468d182f3bae73b625aa659c84e56291b634a58f27ab2ec046e",
        "attributes": {"classe_armatura": "14", "punti_ferita": "9 (2d8)", "velocita": "15 m"},
        "dice": (9, 2, 8, 0),
    },
    "Dolgaunt": {
        "id": "ref_2f8a6bc3d49b510f9b04fe5f414d1abc",
        "page": 293, "stat_page": 293,
        "status": "verified", "corrections": {},
        "checksum": "39b8f59ef3130e83d26baceac2bcf07cc9216efaba65f286e3d0152bd35042f9",
        "hash": "8dabd2f64a29f8c816a4da8a41eb4bce6ae0fe4774d20d5755f59596ab485517",
        "attributes": {"classe_armatura": "16 (Difesa Senza Armatura)", "punti_ferita": "33 (6d8 + 6)", "velocita": "12 m"},
        "dice": (33, 6, 8, 6),
    },
    "Mordakhesh": {
        "id": "ref_0868e1924b1a5417ba0ee221f25069ae",
        "page": 306, "stat_page": 306,
        "status": "needs_review", "corrections": {"_source_changed": True},
        "checksum": "8fdf448a5b52a3c7ff920de9c78894fa835ec2c9c92453a786cb1ba476cefa98",
        "hash": "0dc982962e82ebff4b3159488f51d1d3457da7ba3137d82418198d4741bde430",
        "attributes": {"classe_armatura": "18 (armatura completa)", "punti_ferita": "170 (20d8 + 80)", "velocita": "12 m"},
        "dice": (170, 20, 8, 80),
    },
    "Sul Khatesh": {
        "id": "ref_6a85d321c3a25bfba7d633377b0fccf0",
        "page": 314, "stat_page": 315,
        "status": "verified", "corrections": {},
        "checksum": "77ee5df17eab19b26f2e8cda25814e61c9c1c82f691d94ea7486",
        "hash": "0841402170e004d2b0b7fd3370cb116a4ea423a50c4c2848ab1f857c60a45dec",
        "attributes": {"classe_armatura": "22 (armatura naturale)", "punti_ferita": "475 (50d10 + 200)", "velocita": "12 m, volare 12 m (fluttuare)"},
        "dice": (475, 50, 10, 200),
    },
}


def authority(page: int) -> dict[str, Any]:
    """Original Eberron licensed translation source reference, exact filename."""
    return {
        "page": page, "ruleset": "2014", "filename": SOURCE,
        "source_role": "authority", "logical_page": page,
        "source_title": TITLE, "source_status": "active",
        "authority_class": "licensed_translation",
        "logical_source_id": "erlw_2019_it",
    }


def assess_eberron_reclass(name: str, record: dict[str, Any] | None) -> dict[str, Any]:
    """Read and validate one immutable already-registered source record."""
    if name not in TARGETS or not isinstance(record, dict):
        raise ValueError("missing_or_unregistered_eberron_candidate")
    spec = TARGETS[name]
    expected = {
        "id": spec["id"], "user_id": OWNER,
        "name": name, "normalized_name": name.casefold(), "source_name": name,
        "source_key": SOURCE, "source_language": "it",
        "reference_type": "other", "review_status": spec["status"],
        "review_flags": [], "canonical_id": None,
        "attributes": {}, "source_attributes": {},
        "review_corrections": spec["corrections"],
        "source_text_checksum": spec["checksum"],
        "source_refs": [authority(spec["page"])],
    }
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("sealed_existing_source_snapshot_drift")
    text = record.get("source_full_text")
    if not isinstance(text, str) or text != record.get("full_text"):
        raise ValueError("raw_description_drift")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != spec["hash"]:
        raise ValueError("original_raw_sha256_drift")
    if not text.strip():
        raise ValueError("empty_original_description")
    hp, count, faces, mod = spec["dice"]
    if count * (faces + 1) // 2 + mod != hp:
        raise ValueError("statblock_dice_average_incoherent")
    if monster_semantic_numeric_flags(spec["attributes"]):
        raise ValueError("existing_global_monster_numeric_gate_failed")
    original = [authority(spec["page"])]
    if spec["stat_page"] != spec["page"]:
        original.append(authority(spec["stat_page"]))
    return {
        "record_id": spec["id"], "name": name,
        "status": "eligible_existing_record_reclassification",
        "original_type": "other", "target_type": "monster",
        "description_page": spec["page"], "statblock_page": spec["stat_page"],
        "attributes": spec["attributes"],
        "final_source_refs": original,
        "raw_text_preserved": True, "original_ocr_preserved": True,
        "writes": 0,
    }
