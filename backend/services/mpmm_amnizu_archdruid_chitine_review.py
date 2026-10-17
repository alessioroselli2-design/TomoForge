"""Read-only original MPMM source review of three independent monster boxes.

Three historic other/verified imported rows are not monster-verified, despite
a separate complete boxed creature-statblock on each registered PDF page.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
SOURCE="Mostri del multi verso 1-100.pdf"
TITLE="Mordenkainen Presenta: Mostri del Multiverso"
TARGETS={
    "Amnizu":{
        "id":"ref_c773a569872e5e96a209d1cb9682c9df",
        "page":53,
        "checksum":"40167904715cf2a5517f41d7a06df969ef7f853675c8e642234e5a5cb99791ae",
        "raw_sha":"5aadcd3224866cf469ac61b9b6a94435ed6c62c599d7c2b7ebed011e5926979e",
        "attrs":{"classe_armatura":"21 (armatura naturale)","punti_ferita":"202 (27d8 + 81)","velocita":"9 m, volare 12 m"},
        "dice":(202,27,8,81),
    },
    "Arcidruido":{
        "id":"ref_fadd98159cb95ae3bc7a1c48b3724e6c",
        "page":54,
        "checksum":"145632ff55d85e31b90c0703c042e77ce105eb071718e2583ec96381b26ddab6",
        "raw_sha":"77ca957f8ba6c02711d7729ab710b499cb60f26190763c261d327371a8c5dc98",
        "attrs":{"classe_armatura":"14 (armatura di pelle)","punti_ferita":"154 (28d8 + 28)","velocita":"9 m"},
        "dice":(154,28,8,28),
    },
    "Chitinide":{
        "id":"ref_903c5cfe0459571db2932459217a85c0",
        "page":83,
        "checksum":"60d4074076f24be513770a2613964870752fd7db8780dde245bbc1c32698d144",
        "raw_sha":"8e238430d4b5ade17baac94543a8f44f5d1318c938212686733a9e7febb447eb",
        "attrs":{"classe_armatura":"14 (armatura di pelle)","punti_ferita":"18 (4d6 + 4)","velocita":"9 m, scalare 9 m"},
        "dice":(18,4,6,4),
    },
}

def authority(page:int)->dict[str,Any]:
    return {"page":page,"ruleset":"2014","filename":SOURCE,
    "source_role":"authority","logical_page":page,
    "source_title":TITLE,"source_status":"active",
    "authority_class":"licensed_translation","logical_source_id":"mpmm_2022_it"}


def check_independent_statblock(name:str,row:dict[str,Any]|None)->dict[str,Any]:
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("missing_registered_statblock")
    spec=TARGETS[name]
    required={
        "id":spec["id"],"user_id":OWNER,"name":name,
        "source_name":name,"normalized_name":name.casefold(),
        "reference_type":"other","review_status":"verified",
        "review_flags":[],"canonical_id":None,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":spec["checksum"],
        "source_refs":[authority(spec["page"])],
        "attributes":{},"source_attributes":{},"review_corrections":{},
    }
    if any(row.get(k)!=v for k,v in required.items()):
        raise ValueError("registered_historical_source_changed")
    raw=row.get("full_text")
    if not isinstance(raw,str) or raw!=row.get("source_full_text"):
        raise ValueError("raw_source_text_mutated")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=spec["raw_sha"]:
        raise ValueError("original_source_sha256_changed")
    hp,n,faces,bonus=spec["dice"]
    if n*(faces+1)//2+bonus!=hp:
        raise ValueError("original_hit_dice_average_wrong")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(spec["attrs"]):
        raise ValueError("global_monster_semantic_numeric_gate_failed")
    return {
        "status":"eligible_registered_boxed_monster_reclassification",
        "id":spec["id"],"name":name,
        "source_page":spec["page"],"attrs":spec["attrs"],
        "source_preserved":True,"writes":0,
    }
