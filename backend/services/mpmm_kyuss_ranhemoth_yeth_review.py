"""Fail-closed original-source gate for three MPMM creatures misclassified other.

All three complete named statblocks were independently visually inspected in
the licensed original Italian segment. Review-only module: no database writes.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER = "user_fabf28726a20"
SOURCE = "Mostri del multiverso 201-294.pdf"
TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
TARGETS = {
    "Progenie Di Kyuss": {
        "id": "ref_fd8b27d71d185e6c9c0c02bb7b1eedff",
        "page": 17,
        "flags": ["sezione_potenzialmente_continua"],
        "checksum": "6961faf2e6c64a8c9ef44d6adbc1dff0a02890a85c65a732d4e4199b5fc17be4",
        "raw_sha": "0b69cd08c3906e2486c906fbe22ccfd66d2840140601de4b90498581f7d42d77",
        "attrs": {"classe_armatura":"10","punti_ferita":"76 (9d8 + 36)","velocita":"9 m"},
        "dice": (76,9,8,36),
    },
    "Ranhemoth": {
        "id": "ref_3d64081bf16b57089712def35e7738f1",
        "page": 27,
        "flags": ["sezione_potenzialmente_continua"],
        "checksum": "b110718b14c98045883a0d3cfd24ef76cddba55506252c3189047a49a54793ec",
        "raw_sha": "7d1b7c47addf4fb4dcf5f352de586ef2947334a712f0227716540873ee877141",
        "attrs": {"classe_armatura":"14 (armatura naturale)","punti_ferita":"161 (14d12 + 70)","velocita":"9 m, nuotare 9 m"},
        "dice": (161,14,12,70),
    },
    "Segugio Yeth": {
        "id": "ref_5681e5d9e0165585a05457a3ab8c6901",
        "page": 36,
        "flags": [],
        "checksum": "9652e0ce97d49236af499918e5077c04e3ed9f92bcd4c87ddb961743c4386224",
        "raw_sha": "3ab33651096c2e1ee46407fa8f2a88708ce1c40b230da8a9ac96105425217304",
        "attrs": {"classe_armatura":"14 (armatura naturale)","punti_ferita":"51 (6d10 + 18)","velocita":"12 m, volare 12 m (fluttuare)"},
        "dice": (51,6,10,18),
    },
}


def authority(page: int) -> dict[str, Any]:
    """Match the existing historical licensed source identity exactly."""
    return {
        "page": page, "ruleset": "2014", "filename": SOURCE,
        "source_role": "authority", "logical_page": page + 200,
        "source_title": TITLE, "source_status": "active",
        "authority_class": "licensed_translation",
        "logical_source_id": "mpmm_2022_it",
    }


def review_monster_source(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    """One sealed source snapshot per original record. No state mutation."""
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("missing_or_unregistered_monster")
    t=TARGETS[name]
    original={
        "id":t["id"],"user_id":OWNER,
        "name":name,"source_name":name,"normalized_name":name.casefold(),
        "reference_type":"other","review_status":"needs_review",
        "review_flags":t["flags"],"canonical_id":None,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":t["checksum"],
        "source_refs":[authority(t["page"])],
        "attributes":{},"source_attributes":{},
        "review_corrections":{"_source_changed":True},
    }
    if any(row.get(key)!=val for key,val in original.items()):
        raise ValueError("historical_original_source_snapshot_changed")
    text=row.get("full_text")
    if not isinstance(text,str) or text!=row.get("source_full_text"):
        raise ValueError("original_raw_description_modified")
    if hashlib.sha256(text.encode("utf-8")).hexdigest()!=t["raw_sha"]:
        raise ValueError("original_source_SHA256_mismatch")
    hp,n,faces,bonus=t["dice"]
    if (n*(faces+1))//2+bonus!=hp:
        raise ValueError("boxed_original_HP_math_failed")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(t["attrs"]):
        raise ValueError("existing_global_identity_or_numeric_gate_failed")
    return {
        "id":t["id"],"name":name,
        "status":"eligible_source_locked_monster_reclassification",
        "logical_page":t["page"]+200,
        "attributes":t["attrs"],"previous_ocr_flag_preserved_in_audit":t["flags"],
        "raw_source_preserved":True,"writes":0,
    }
