"""Source-locked no-write audits for three separate Italian MPMM monster boxes.

Existing rows were marked other/verified without creature attributes, and
Titivilus statblock follows its prose on the next PDF page (p56, ref p55).
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER = "user_fabf28726a20"
TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
TARGETS = {
    "Bacio Della Morte": {
        "id": "ref_5f2cb6c93efc52ee93321ec5bab27cdc",
        "file": "Mostri del multi verso 1-100.pdf",
        "ref_page": 59, "stat_page": 59, "logical": 59,
        "checksum": "92387ad421276e393b06c2ea8c662c8b7d2775f8212f4b627ab865a5a1d04fae",
        "raw_sha": "12ef489b445acbc2dafaecce5ad46a09782eb30356c4b54e60b8df0e841c0fbe",
        "attrs": {"classe_armatura":"15 (armatura naturale)","punti_ferita":"142 (15d10 + 60)","velocita":"0 m, volare 9 m (fluttuare)"},
        "dice": (142,15,10,60),
    },
    "Sacerdote Di Guerra": {
        "id": "ref_bf6be8fa7c795ea19cb45c979c4b21b6",
        "file": "Mostri del multiverso 201-294.pdf",
        "ref_page": 32, "stat_page": 32, "logical": 232,
        "checksum": "7b2520a2d51a02294a77ad9f5b6b77f00de9fc1cea2a09c4e9ceac1600b3e2aa",
        "raw_sha": "a1289c6a87f1ed55d007ef4d9b97eec24e8351831e2d930cf6beb8a53fb1120c",
        "attrs": {"classe_armatura":"18 (piastre)","punti_ferita":"117 (18d8 + 36)","velocita":"9 m"},
        "dice": (117,18,8,36),
    },
    "Titivilus": {
        "id": "ref_d074c01ca79d50d5afda4e45ea48da71",
        "file": "Mostri del multiverso 201-294.pdf",
        "ref_page": 55, "stat_page": 56, "logical": 255,
        "checksum": "a7f71701a4bf1b52a38a5fdb7e384b369eacb8d8cd0867fe7f104ad1d54a4e4a",
        "raw_sha": "0ed58d7a31ef7a20f7007ef9ed7f9ff22907c8f2ae5a13b95e4814e745059fcd",
        "attrs": {"classe_armatura":"20 (armatura naturale)","punti_ferita":"150 (20d8 + 60)","velocita":"12 m, volare 18 m"},
        "dice": (150,20,8,60),
    },
}

def registered_ref(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": spec["ref_page"], "ruleset":"2014",
        "filename":spec["file"],"source_role":"authority",
        "logical_page":spec["logical"],"source_title":TITLE,
        "source_status":"active","authority_class":"licensed_translation",
        "logical_source_id":"mpmm_2022_it",
    }


def audit_creature(name: str, original: dict[str, Any] | None) -> dict[str, Any]:
    if name not in TARGETS or not isinstance(original,dict):
        raise ValueError("source_creature_not_registered")
    t=TARGETS[name]
    expected = {
        "id":t["id"],"user_id":OWNER,
        "name":name,"source_name":name,"normalized_name":name.casefold(),
        "reference_type":"other","review_status":"verified",
        "review_flags":[],"canonical_id":None,
        "source_key":t["file"],"source_language":"it",
        "source_text_checksum":t["checksum"],
        "source_refs":[registered_ref(t)],"attributes":{},
        "source_attributes":{},"review_corrections":{},
    }
    if any(original.get(k)!=v for k,v in expected.items()):
        raise ValueError("original_other_verified_snapshot_drift")
    raw=original.get("full_text")
    if not isinstance(raw,str) or raw!=original.get("source_full_text"):
        raise ValueError("historical_source_text_drift")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=t["raw_sha"]:
        raise ValueError("historical_original_sha256_drift")
    hp,n,faces,bonus=t["dice"]
    if n*(faces+1)//2+bonus!=hp:
        raise ValueError("named_original_dice_average_failed")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(t["attrs"]):
        raise ValueError("global_identity_or_numeric_gate_failed")
    return {
        "status":"eligible_separately_named_original_statblock",
        "id":t["id"],"name":name,"source_ref_page":t["ref_page"],
        "independent_statblock_page":t["stat_page"],
        "attrs":t["attrs"],"source_fields_immutable":True,"writes":0,
    }
