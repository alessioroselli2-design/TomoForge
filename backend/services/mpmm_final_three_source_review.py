"""Read-only registered-source review of three missing Italian MPMM creature statblocks.

Alkilith and Derro Sapiente were absent from the imported records; Bardo was
imported as a class although the licensed original names a distinct NPC
statblock. The original source file is user-provided and already catalogued.
No database writes occur here.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER = "user_fabf28726a20"
SOURCE = "Mostri del multi verso 1-100.pdf"
LOGICAL = "mpmm_2022_it"
BARD_ID = "ref_23f704804c1059e4becdde28c0b01061"
BARD_SHA = "95239fe4c61d282d82e10a69edc784b3419e2883075fc6fef633c071b72a6111"
BARD_CHECKSUM = "05e4578077a78782da4259ea1ed8bc563e17055a98ffb609f741eacfc02f016b"

TARGETS = {
    "Alkilith": {
        "id":"ref_9ac0f7f7d27ecb4fe52b952b8a22650f", "page":51,
        "source_excerpt":"Immondo Medio (demone), generalmente caotico malvagio. Classe Armatura 17 (armatura naturale). Punti Ferita 168 (16d8 + 96). Velocità 12 m, scalare 12 m.",
        "excerpt_sha256":"b163841502bf6395765514458013d743caff1e28df4a07c024d734a5eb963bce",
        "attrs":{"classe_armatura":"17 (armatura naturale)","punti_ferita":"168 (16d8 + 96)","velocita":"12 m, scalare 12 m"},
        "dice":(168,16,8,96),
    },
    "Derro Sapiente": {
        "id":"ref_16f2969009bd295552e09d79480cbe34", "page":94,
        "source_excerpt":"Aberrazione Piccola (stregone), generalmente caotica malvagia. Classe Armatura 13 (armatura di cuoio). Punti Ferita 36 (8d6 + 8). Velocità 9 m.",
        "excerpt_sha256":"db2e83636885a777938aff5de9e939f06f5a2fc5e0fbc15e25aaf8c07c2b0d44",
        "attrs":{"classe_armatura":"13 (armatura di cuoio)","punti_ferita":"36 (8d6 + 8)","velocita":"9 m"},
        "dice":(36,8,6,8),
    },
}
BARD_ATTRIBUTES={"classe_armatura":"15 (giaco di maglia)","punti_ferita":"44 (8d8 + 8)","velocita":"9 m"}


def authority(page: int) -> dict[str, Any]:
    return {
        "page":page,"ruleset":"2014","filename":SOURCE,
        "source_role":"authority","logical_page":page,
        "source_title":"Mordenkainen Presenta: Mostri del Multiverso",
        "source_status":"active","authority_class":"licensed_translation",
        "logical_source_id":LOGICAL,
    }


def audit_catalog(catalog: dict[str,Any] | None) -> None:
    required={"logical_source_id":LOGICAL,"physical_filename":SOURCE,
        "physical_pages":100,"source_status":"active",
        "authority_class":"licensed_translation","source_role":"authority"}
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in required.items()):
        raise ValueError("registered_Italian_original_source_mismatch")


def audit_new_creature(name: str, existing_id: dict[str,Any] | None,
                       existing_name: dict[str,Any] | None,
                       catalog: dict[str,Any] | None) -> dict[str,Any]:
    if name not in TARGETS:
        raise ValueError("unregistered_creature")
    if existing_id is not None or existing_name is not None:
        raise ValueError("duplicate_or_conflicting_creature")
    audit_catalog(catalog)
    t=TARGETS[name]
    token=f"{LOGICAL}|{SOURCE}|{t['page']}|{name.casefold()}"
    if "ref_"+hashlib.sha256(token.encode()).hexdigest()[:32]!=t["id"]:
        raise ValueError("deterministic_identity_drift")
    if hashlib.sha256(t["source_excerpt"].encode()).hexdigest()!=t["excerpt_sha256"]:
        raise ValueError("manual_original_visual_excerpt_modified")
    hp,n,faces,bonus=t["dice"]
    if n*(faces+1)//2+bonus!=hp:
        raise ValueError("original_hit_dice_math_failed")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(t["attrs"]):
        raise ValueError("unchanged_global_identity_or_numeric_gate_failed")
    return {
      "status":"eligible_new_source_named_monster",
      "name":name,"id":t["id"],"page":t["page"],
      "attributes":t["attrs"],"manual_visual_transcription":True,
      "automatic_OCR_not_claimed":True,"writes":0,
    }


def audit_bard(original: dict[str,Any] | None) -> dict[str,Any]:
    if not isinstance(original,dict):
        raise ValueError("original_Bardo_record_absent")
    required={
        "id":BARD_ID,"user_id":OWNER,"name":"Bardo",
        "source_name":"Bardo","normalized_name":"bardo",
        "reference_type":"class","review_status":"verified",
        "review_flags":[],"canonical_id":None,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":BARD_CHECKSUM,
        "source_refs":[authority(66)],"attributes":{},"source_attributes":{},
        "review_corrections":{},
    }
    if any(original.get(k)!=v for k,v in required.items()):
        raise ValueError("original_NPC_misclassification_snapshot_drift")
    raw=original.get("full_text")
    if not isinstance(raw,str) or raw!=original.get("source_full_text"):
        raise ValueError("original_Bardo_raw_changed")
    if hashlib.sha256(raw.encode()).hexdigest()!=BARD_SHA:
        raise ValueError("source_Bardo_prose_sha256_mismatch")
    if monster_identity_sanity_flags("Bardo") or monster_semantic_numeric_flags(BARD_ATTRIBUTES):
        raise ValueError("Bardo_global_numeric_gate_failed")
    if (8*9)//2+8!=44:
        raise ValueError("Bardo_source_HP_math_failed")
    return {"status":"eligible_bard_NPC_reclassification","name":"Bardo","id":BARD_ID,
            "original_classification_preserved_in_history":True,
            "attributes":BARD_ATTRIBUTES,"writes":0}
