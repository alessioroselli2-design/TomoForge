"""Protected source review for Tasha's distinct mighty servant creature.

Original Italian user-provided 194-page Tasha PDF, named boxed statblock on
physical page 131: Servitore Possente di Leuk-O, Huge Construct. Read-only.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
NAME="Servitore Possente Di Leuk-O"
ID="ref_7e3e59d442377464d2d5d1a92a45cbe8"
SOURCE="Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf"
CATALOG_FILE="Calderone-Omnicomprensivo-di-TASHA.pdf"
SOURCE_ID="tce_2020_it"
PAGE=131
EXCERPT="Costrutto Enorme. Classe Armatura 22 (armatura naturale). Punti Ferita 310 (27d12 + 135). Velocità 18 m."
EXCERPT_SHA="64b11217724339154d33016189ee4bba1dd7986793c0fa96731a6d9ea937d70a"
ATTRS={"classe_armatura":"22 (armatura naturale)","punti_ferita":"310 (27d12 + 135)","velocita":"18 m"}

def audit_leuko_source(existing_id:dict[str,Any]|None,existing_name:dict[str,Any]|None,catalog:dict[str,Any]|None)->dict[str,Any]:
    if existing_id is not None or existing_name is not None:
        raise ValueError("duplicate_monster_record")
    if not isinstance(catalog,dict):
        raise ValueError("original_source_catalog_unavailable")
    expected={
        "logical_source_id":SOURCE_ID,"physical_filename":CATALOG_FILE,
        "physical_pages":194,"source_role":"authority",
        "source_status":"active","authority_class":"licensed_translation",
    }
    if any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("licensed_catalog_changed")
    token=f"{SOURCE_ID}|{SOURCE}|{PAGE}|{NAME.casefold()}"
    if "ref_"+hashlib.sha256(token.encode()).hexdigest()[:32]!=ID:
        raise ValueError("new_id_source_determinism_failed")
    if hashlib.sha256(EXCERPT.encode()).hexdigest()!=EXCERPT_SHA:
        raise ValueError("source_visual_excerpt_sha256_drift")
    if monster_identity_sanity_flags(NAME) or monster_semantic_numeric_flags(ATTRS):
        raise ValueError("global_numeric_or_identity_gate_failed")
    if (27*(12+1))//2+135!=310:
        raise ValueError("exact_hit_dice_math_failed")
    return {
       "status":"eligible_new_manual_visual_creature",
       "id":ID,"name":NAME,"source_page":PAGE,
       "attributes":ATTRS,"automatic_ocr_not_claimed":True,
       "original_catalog_preserved":True,"writes":0,
    }
