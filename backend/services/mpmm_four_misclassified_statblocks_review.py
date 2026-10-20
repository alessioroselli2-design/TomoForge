"""Original-source, no-write review of four misclassified Italian MPMM monsters.

The exact registered PDFs were visually inspected at physical pp47, 50, 53, 67.
Each holds its own named boxed monster AC/HP/speed block.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags,monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
SOURCE="Mostri del multiverso 201-294.pdf"
TITLE="Mordenkainen Presenta: Mostri del Multiverso"
TARGETS={
    "Somiero Gigante":{
        "id":"ref_4d118233f6ec526f9fce6752d80a0015",
        "page":47,"type":"other","flags":["sezione_potenzialmente_continua"],
        "checksum":"6a1f8ddcebb711674c1ab383da91617706acef376f9bd6c3737627c417d29ae6",
        "sha":"7d248ab550a1216f1cfbeb1d76e628e91a9f44892b23d42b77fb3c24b23b8b32",
        "corrections":{},
        "attrs":{"classe_armatura":"14 (armatura naturale)","punti_ferita":"22 (3d10 + 6)","velocita":"15 m"},
        "dice":(22,3,10,6),
    },
    "Tanarukk":{
        "id":"ref_1c35bd27feb850a6a57ab3477a99cdd1",
        "page":50,"type":"other","flags":[],
        "checksum":"f4fc5f2b9e96675cf90022269ba5f44461ac4b3fbf299c99fced7c6857931609",
        "sha":"3259afd2e4a1e021eaf9faf96d20630367dc20213ad749b11a264e7350e8a69a",
        "corrections":{"_source_changed":True},
        "attrs":{"classe_armatura":"14 (armatura naturale)","punti_ferita":"95 (10d8 + 50)","velocita":"9 m"},
        "dice":(95,10,8,50),
    },
    "Terrore Gigante Di Fuoco":{
        "id":"ref_e870c9a40ffa5c39b9fee58513a3e7b5",
        "page":53,"type":"other","flags":["sezione_potenzialmente_continua"],
        "checksum":"0af5e54731c5ad3c2568ec99a4d7e5505deeaf671f8ea2289997f4314ebdf1a2",
        "sha":"5763ef753e3c93a5add9a70f6fd63485b077f0a5097ecfeb79236ad694b3618f",
        "corrections":{"_source_changed":True},
        "attrs":{"classe_armatura":"21 (piastre, duplice scudo)","punti_ferita":"187 (15d12 + 90)","velocita":"9 m"},
        "dice":(187,15,12,90),
    },
    "Venator":{
        "id":"ref_dc9a60dbe52a5ebf9310495c61e60fae",
        "page":67,"type":"ability","flags":[],
        "checksum":"a1a9870c756485e233098f731bf1b110dec577ea8f8b7443a70dcf3df39c2b05",
        "sha":"beebd819a226887e78f9c8bbad9a728b7526b37b32b291e0d06a769b19b7d1a2",
        "corrections":{"_source_changed":True},
        "attrs":{"classe_armatura":"13 (armatura naturale)","punti_ferita":"68 (8d10 + 24)","velocita":"6 m, scalare 6 m"},
        "dice":(68,8,10,24),
    },
}


def authority(page:int)->dict[str,Any]:
    return {
        "page":page,"ruleset":"2014","filename":SOURCE,
        "source_role":"authority","logical_page":page+200,
        "source_title":TITLE,"source_status":"active",
        "authority_class":"licensed_translation",
        "logical_source_id":"mpmm_2022_it",
    }


def review_named_statblock(name:str,row:dict[str,Any]|None)->dict[str,Any]:
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("missing_unregistered_candidate")
    s=TARGETS[name]
    expected={
        "id":s["id"],"user_id":OWNER,"name":name,
        "source_name":name,"normalized_name":name.casefold(),
        "reference_type":s["type"],"review_status":"needs_review",
        "review_flags":s["flags"],"canonical_id":None,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":s["checksum"],
        "source_refs":[authority(s["page"])],
        "attributes":{},"source_attributes":{},
        "review_corrections":s["corrections"],
    }
    if any(row.get(k)!=v for k,v in expected.items()):
        raise ValueError("registered_original_monster_source_snapshot_changed")
    raw=row.get("full_text")
    if not isinstance(raw,str) or raw!=row.get("source_full_text"):
        raise ValueError("raw_narrative_changed")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=s["sha"]:
        raise ValueError("raw_sha256_changed")
    hp,count,faces,bonus=s["dice"]
    if (count*(faces+1))//2+bonus!=hp:
        raise ValueError("original_named_statblock_HP_average_failed")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(s["attrs"]):
        raise ValueError("original_global_identity_numeric_gates_failed")
    return {
        "id":s["id"],"name":name,
        "status":"eligible_original_boxed_monster_reclassification",
        "logical_source_page":s["page"]+200,
        "original_type":s["type"],"original_flags":s["flags"],
        "correct_attributes":s["attrs"],
        "raw_source_preserved":True,"writes":0,
    }
