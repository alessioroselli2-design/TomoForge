"""Fail-closed, no-write audit of original Italian MPMM Yagnoloth statblock."""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags,monster_semantic_numeric_flags

NAME="Yagnoloth"
ID="ref_8ca7c91e877e5690a7a09358e74ce418"
OWNER="user_fabf28726a20"
SOURCE="Mostri del multiverso 201-294.pdf"
CHECKSUM="1dbe5f699db96926536ee041bdcea40deea5570e3abd3a72f258cb577e686a96"
RAW_SHA="d3eb7c299bcf8f2cac16a051b4f56d4f30c7cc6b277215b64e1212cea84019da"
ATTRS={"classe_armatura":"17 (armatura naturale)","punti_ferita":"147 (14d10 + 70)","velocita":"12 m"}
REF={
    "page":72,"ruleset":"2014","filename":SOURCE,"source_role":"authority",
    "logical_page":272,"source_title":"Mordenkainen Presenta: Mostri del Multiverso",
    "source_status":"active","authority_class":"licensed_translation",
    "logical_source_id":"mpmm_2022_it",
}

def review_yagnoloth_source(row:dict[str,Any]|None)->dict[str,Any]:
    if not isinstance(row,dict):
        raise ValueError("missing_original_yagnoloth")
    expected={
        "id":ID,"user_id":OWNER,"name":NAME,"source_name":NAME,
        "normalized_name":NAME.casefold(),"reference_type":"other",
        "review_status":"needs_review","review_flags":[],
        "canonical_id":None,"source_key":SOURCE,"source_language":"it",
        "source_text_checksum":CHECKSUM,"source_refs":[REF],
        "attributes":{},"source_attributes":{},
        "review_corrections":{"_source_changed":True},
    }
    if any(row.get(k)!=v for k,v in expected.items()):
        raise ValueError("historical_original_source_drift")
    text=row.get("full_text")
    if not isinstance(text,str) or text!=row.get("source_full_text"):
        raise ValueError("original_raw_description_modified")
    if hashlib.sha256(text.encode("utf-8")).hexdigest()!=RAW_SHA:
        raise ValueError("source_raw_sha256_changed")
    if (14*(10+1))//2+70!=147:
        raise ValueError("original_HP_dice_average_mismatch")
    if monster_identity_sanity_flags(NAME) or monster_semantic_numeric_flags(ATTRS):
        raise ValueError("strict_global_identity_numeric_gate_failed")
    return {
        "id":ID,"name":NAME,"source_page":272,
        "status":"eligible_original_source_monster_reclassification",
        "attributes":ATTRS,"original_source_unchanged":True,"writes":0,
    }
