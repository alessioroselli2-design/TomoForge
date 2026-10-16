"""Read-only source audit for MPMM Neotelide, misclassified as other.

Licensed original Italian PDF part 201-294 physical page 1 contains the full
boxed named Neotelide statblock, despite an inherited continuation OCR flag.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

ID = "ref_bed5d732599154428a550ff35f17930c"
OWNER = "user_fabf28726a20"
NAME = "Neotelide"
SOURCE = "Mostri del multiverso 201-294.pdf"
CHECKSUM = "8edb69f839961f9beca9b2a8c0f9f859fcf9086a8f3bb7815e9080417fb82ca5"
SOURCE_SHA = "23b4037d7ce0274a5ffdfada51d3a94236ba17079dac31ceb5833fd29ea2a767"
ATTRS = {
    "classe_armatura": "16 (armatura naturale)",
    "punti_ferita": "232 (15d20 + 75)",
    "velocita": "9 m",
}
REF = {
    "page":1,"ruleset":"2014","filename":SOURCE,"source_role":"authority",
    "logical_page":201,"source_title":"Mordenkainen Presenta: Mostri del Multiverso",
    "source_status":"active","authority_class":"licensed_translation",
    "logical_source_id":"mpmm_2022_it",
}

def assess_neotelide(row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row,dict):
        raise ValueError("registered_creature_absent")
    expected={
        "id":ID,"user_id":OWNER,"name":NAME,"source_name":NAME,
        "normalized_name":NAME.casefold(),
        "reference_type":"other","review_status":"needs_review",
        "review_flags":["sezione_potenzialmente_continua"],
        "canonical_id":None,"source_key":SOURCE,"source_language":"it",
        "source_text_checksum":CHECKSUM,"source_refs":[REF],
        "review_corrections":{"_source_changed":True},
        "attributes":{},"source_attributes":{},
    }
    if any(row.get(k)!=v for k,v in expected.items()):
        raise ValueError("original_neotelide_source_drift")
    raw=row.get("full_text")
    if not isinstance(raw,str) or raw!=row.get("source_full_text"):
        raise ValueError("historical_source_changed")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=SOURCE_SHA:
        raise ValueError("registered_raw_source_hash_changed")
    if monster_identity_sanity_flags(NAME) or monster_semantic_numeric_flags(ATTRS):
        raise ValueError("global_identity_or_numeric_gate_failed")
    if (15*21)//2+75!=232:
        raise ValueError("original_HP_math_wrong")
    return {
        "status":"eligible_original_named_statblock",
        "name":NAME,"id":ID,"page":201,
        "attributes":ATTRS,"resolves_stale_continuation_flag":True,
        "raw_source_preserved":True,"writes":0,
    }
