"""Strict no-write reviews of two omitted original Italian MPMM mage monsters.

Historical imported references are other/verified from shared descriptive p68.
Independently named boxed creature statblocks are on PDF pages 70 and 73.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
SOURCE="Mostri del multiverso 101-200.pdf"
TITLE="Mordenkainen Presenta: Mostri del Multiverso"
TARGETS={
    "Mago Evocatore":{
        "id":"ref_6a3e5d9b0f5357509f30977d89205f47",
        "ref_page":68,"stat_page":70,
        "checksum":"ed84e361dcd679c0fcc1a26669d2bd0a19b92fbfca4b3125b6dfe6ea4e4e2eef",
        "raw_sha":"f1882d3d94c4057fbd21be0b47d9699f3ac84363d4dea7fab922f0b49f9af7e8",
        "attrs":{"classe_armatura":"12 (15 con armatura magica)","punti_ferita":"58 (13d8)","velocita":"9 m"},
        "dice":(58,13,8,0),
    },
    "Mago Necromante":{
        "id":"ref_6ca54072adc75b1c8bd4f5943fbaafbb",
        "ref_page":68,"stat_page":73,
        "checksum":"b52d97f0c57dfcab5db09f9e83aa016f2d0aa67274c142c5c21a06d75d4bdbda",
        "raw_sha":"7efaa6915be235fbdb02f90b8508ed87736373397fcb30c193664581089536a7",
        "attrs":{"classe_armatura":"12 (15 con armatura magica)","punti_ferita":"110 (20d8 + 20)","velocita":"9 m"},
        "dice":(110,20,8,20),
    },
}

def authority()->dict[str,Any]:
    return {
        "page":68,"ruleset":"2014","filename":SOURCE,
        "source_role":"authority","logical_page":168,
        "source_title":TITLE,"source_status":"active",
        "authority_class":"licensed_translation",
        "logical_source_id":"mpmm_2022_it",
    }

def verify_named_boxed_mage(name:str,row:dict[str,Any]|None)->dict[str,Any]:
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("original_mage_missing")
    spec=TARGETS[name]
    expected={
        "id":spec["id"],"user_id":OWNER,
        "name":name,"source_name":name,"normalized_name":name.casefold(),
        "reference_type":"other","review_status":"verified",
        "review_flags":[],"canonical_id":None,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":spec["checksum"],
        "source_refs":[authority()],
        "attributes":{},"source_attributes":{},"review_corrections":{},
    }
    if any(row.get(k)!=v for k,v in expected.items()):
        raise ValueError("historical_source_snapshot_mismatch")
    raw=row.get("full_text")
    if not isinstance(raw,str) or raw!=row.get("source_full_text"):
        raise ValueError("original_text_changed")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=spec["raw_sha"]:
        raise ValueError("original_raw_sha_drift")
    hp,n,sides,bonus=spec["dice"]
    if n*(sides+1)//2+bonus!=hp:
        raise ValueError("original_hit_dice_math_invalid")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(spec["attrs"]):
        raise ValueError("global_monster_gate_failed")
    return {
        "status":"eligible_independent_original_mage_monster",
        "id":spec["id"],"name":name,
        "registered_description_page":168,
        "actual_statblock_page":100+spec["stat_page"],
        "attributes":spec["attrs"],"original_preserved":True,"writes":0,
    }
