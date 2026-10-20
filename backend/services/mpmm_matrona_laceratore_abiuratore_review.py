"""Strict readonly MPMM original-source reviews of three monster statblocks.

Historical imported rows are other/verified without monster attributes.
Drow Matrona Madre original prose is on p6, but named boxed stats on p7.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
SOURCE="Mostri del multiverso 101-200.pdf"
TITLE="Mordenkainen Presenta: Mostri del Multiverso"
TARGETS={
    "Drow Matrona Madre":{
        "id":"ref_c4f30d927d285db1a0b3707234597455",
        "ref_page":6,"stat_page":7,
        "checksum":"145b16ada3f0f1c2b641aa05b4f710fcb182b4f8a825b0ffcfc7348fca4976ae",
        "raw_sha":"c83821e32c80e138c4e350dc569932c0d0c4c1308da30c1af36c3f7326884b93",
        "attrs":{"classe_armatura":"17 (mezza armatura)","punti_ferita":"247 (33d8 + 99)","velocita":"9 m"},
        "dice":(247,33,8,99),
    },
    "Laceratore Grigio":{
        "id":"ref_5fa8f97ba31b5bdb8be257518f28cead",
        "ref_page":62,"stat_page":62,
        "checksum":"70ebce385266ab55a3f62983c42f3b33c13e7d6988c8b24ffee12012fd4c4365",
        "raw_sha":"4ab1a513e680bbfb55534406f27ef11b0858948b5d87c3ea20a39c955a5fab62",
        "attrs":{"classe_armatura":"19 (armatura naturale)","punti_ferita":"189 (18d10 + 90)","velocita":"9 m"},
        "dice":(189,18,10,90),
    },
    "Mago Abiuratore":{
        "id":"ref_408f4c25e39d5c68b8a1389f8f0c17e3",
        "ref_page":68,"stat_page":68,
        "checksum":"95529e965f3821ccadcc7c4b2421ed40768abf6705dacc940927146d276982ff",
        "raw_sha":"09ba2dd9e896617e25e1f1e1440cc8f42287f3cb082c78e7fd53e9ee0b83b2a1",
        "attrs":{"classe_armatura":"12 (15 con armatura magica)","punti_ferita":"104 (16d8 + 32)","velocita":"9 m"},
        "dice":(104,16,8,32),
    },
}

def registered_ref(page:int)->dict[str,Any]:
    return {
        "page":page,"ruleset":"2014","filename":SOURCE,
        "source_role":"authority","logical_page":100+page,
        "source_title":TITLE,"source_status":"active",
        "authority_class":"licensed_translation",
        "logical_source_id":"mpmm_2022_it",
    }

def inspect_named_original(name:str,row:dict[str,Any]|None)->dict[str,Any]:
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("registered_original_missing")
    spec=TARGETS[name]
    required={
        "id":spec["id"],"user_id":OWNER,
        "name":name,"source_name":name,"normalized_name":name.casefold(),
        "reference_type":"other","review_status":"verified",
        "review_flags":[],"canonical_id":None,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":spec["checksum"],
        "source_refs":[registered_ref(spec["ref_page"])],
        "attributes":{},"source_attributes":{},"review_corrections":{},
    }
    if any(row.get(k)!=v for k,v in required.items()):
        raise ValueError("original_registered_source_snapshot_mismatch")
    raw=row.get("full_text")
    if not isinstance(raw,str) or raw!=row.get("source_full_text"):
        raise ValueError("original_source_changed")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=spec["raw_sha"]:
        raise ValueError("source_raw_sha256_drift")
    hp,n,faces,bonus=spec["dice"]
    if n*(faces+1)//2+bonus!=hp:
        raise ValueError("independent_boxed_HP_math_error")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(spec["attrs"]):
        raise ValueError("existing_global_identity_or_numeric_gate_failed")
    return {
        "status":"eligible_original_boxed_monster",
        "id":spec["id"],"name":name,
        "registered_source_page":100+spec["ref_page"],
        "actual_named_statblock_page":100+spec["stat_page"],
        "attrs":spec["attrs"],"original_immutable":True,"writes":0,
    }
