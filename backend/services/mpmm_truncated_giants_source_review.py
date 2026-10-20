"""Read-only source audit restoring two truncated original Italian MPMM giant names.

Both licensed original PDF pages contain fully named, distinct boxed creature
statistics; existing OCR-import source_name remains immutable after review.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
TITLE="Mordenkainen Presenta: Mostri del Multiverso"
TARGETS={
    "Gigante Delle Nuvole Sorridente":{
        "id":"ref_132ae81e5de45b409f5813827e52f314",
        "old_name":"Sorridente","file":"Mostri del multiverso 101-200.pdf",
        "page":32,"logical_page":132,
        "checksum":"d7409a01328c11a1d900c530d33dfc7614023831cce87fd7927c9ebabe768383",
        "raw_sha":"08c43aea9e8de54ffa49d443361a6f01afa7e19a5139405e1286b3d3e9a2e47c",
        "attrs":{"classe_armatura":"15 (armatura naturale)","punti_ferita":"250 (20d12 + 120)","velocita":"12 m, volare 12 m (fluttuare)"},
        "dice":(250,20,12,120),
    },
    "Quintessenza Di Gigante Delle Tempeste":{
        "id":"ref_831472217c475be0b44d30b7b1b76302",
        "old_name":"Delle Tempeste","file":"Mostri del multiverso 201-294.pdf",
        "page":24,"logical_page":224,
        "checksum":"73b1bdaa15049cf19ee70de476d427c29d8f7e2276099f1398c455bb019067f1",
        "raw_sha":"4bf297bcf87aaa6f0eb10efb4432bbfea8baeb88c0161582b19cfe410ac43f9d",
        "attrs":{"classe_armatura":"12","punti_ferita":"230 (20d12 + 100)","velocita":"15 m, volare 15 m (fluttuare), nuotare 15 m"},
        "dice":(230,20,12,100),
    },
}

def authority(spec:dict[str,Any])->dict[str,Any]:
    return {
        "page":spec["page"],"ruleset":"2014","filename":spec["file"],
        "source_role":"authority","logical_page":spec["logical_page"],
        "source_title":TITLE,"source_status":"active",
        "authority_class":"licensed_translation",
        "logical_source_id":"mpmm_2022_it",
    }

def inspect_giant(name:str,row:dict[str,Any]|None)->dict[str,Any]:
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("giant_source_record_not_registered")
    spec=TARGETS[name]
    expected={
        "id":spec["id"],"user_id":OWNER,
        "name":spec["old_name"],"source_name":spec["old_name"],
        "normalized_name":spec["old_name"].casefold(),
        "reference_type":"other","review_status":"needs_review",
        "review_flags":[],"canonical_id":None,
        "source_key":spec["file"],"source_language":"it",
        "source_text_checksum":spec["checksum"],
        "source_refs":[authority(spec)],
        "attributes":{},"source_attributes":{},
        "review_corrections":{"_source_changed":True},
    }
    if any(row.get(key)!=val for key,val in expected.items()):
        raise ValueError("registered_original_short_name_snapshot_changed")
    raw=row.get("full_text")
    if not isinstance(raw,str) or raw!=row.get("source_full_text"):
        raise ValueError("original_prose_modified")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=spec["raw_sha"]:
        raise ValueError("registered_raw_sha256_drift")
    hp,n,faces,bonus=spec["dice"]
    if n*(faces+1)//2+bonus!=hp:
        raise ValueError("independent_named_giant_HP_dice_math_invalid")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(spec["attrs"]):
        raise ValueError("unchanged_global_monster_semantic_gate_failed")
    return {
        "status":"eligible_full_title_original_giant_monster",
        "record_id":spec["id"],"original_name":spec["old_name"],
        "correct_name":name,"logical_page":spec["logical_page"],
        "attrs":spec["attrs"],"source_name_preserved":True,"writes":0,
    }
