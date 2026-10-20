"""Read-only source-locked correction of three already-verified wrong neighbor stats.

The historical 'verified' status is preserved; two Serramorte subtypes
inherited the base Serramorte stats, and Danzatore Dell'Ombra inherited the
adjacent Shadar-Kai Tessitore Di Tenebre stats. The original source text,
authority refs, OCR source attributes and all earlier review history remain.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

SOURCE = "Mostri del multiverso 201-294.pdf"
USER = "user_fabf28726a20"
TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
TARGETS = {
    "Serramorte Stratega": {
        "id": "ref_4ac989c3b0765a0592ddaa468bbd4a22",
        "pages": [37,38],
        "checksum": "cb524d057c16b31cf85646d835fe3ce2675872d75e25e4eb277db53720d1c827",
        "raw_sha": "eb36c0280dc7795d75e5ee75392f62246024c9d6786ed04e58ceeed04240e2e3",
        "original_attrs": {"classe_armatura":"12 (15 con armatura magica)","punti_ferita":"36 (8d8)","velocita":"9 m"},
        "source_attrs": {"classe_armatura":"1","punti_ferita":"1","velocita":"9 m"},
        "corrections": {"_source_changed": True},
        "proper_attrs": {"classe_armatura":"13 (16 con armatura magica)","punti_ferita":"110 (20d8 + 20)","velocita":"9 m"},
        "dice": (110,20,8,20),
        "misattributed": "Serramorte",
    },
    "Serramorte Wight": {
        "id": "ref_a60dc23c311254ffa56cf312de6d1da5",
        "pages": [37,38],
        "checksum": "28482bab2cbff98e3de36a1ef8e664e75d19b7e8377ce72ee74665a6fcf1e21b",
        "raw_sha": "b0d8ddd08e18110e73cb4e872eea8547856e389db8d558716b2082daa01bf683",
        "original_attrs": {"classe_armatura":"12 (15 con armatura magica)","punti_ferita":"36 (8d8)","velocita":"9 m"},
        "source_attrs": {"classe_armatura":"12 (1 5 con armatura magica)","punti_ferita":"37 (5d8 + 1 5)","velocita":"9 m"},
        "corrections": {"_source_changed": True},
        "proper_attrs": {"classe_armatura":"12 (15 con armatura magica)","punti_ferita":"37 (5d8 + 15)","velocita":"9 m"},
        "dice": (37,5,8,15),
        "misattributed": "Serramorte",
    },
    "Danzatore Dell'Ombra": {
        "id": "ref_a6f22b9706e058a8bd3f4dcbbd24c985",
        "pages": [40],
        "checksum": "1e9b6c1efc2aeb4f4aa31993de7c827aae4213254f18e415ed2fa09f65c392f1",
        "raw_sha": "b4c6db66962329cc5d40c80f33bd5a7c7fc19c76766b3abdff012a44b74359e0",
        "original_attrs": {"classe_armatura":"14 (17 con armatura magica)","punti_ferita":"104 (16d8 + 32)","velocita":"9 m"},
        "source_attrs": {},
        "corrections": {},
        "proper_attrs": {"classe_armatura":"15 (cuoio borchiato)","punti_ferita":"71 (13d8 + 13)","velocita":"9 m"},
        "dice": (71,13,8,13),
        "misattributed": "Shadar-Kai Tessitore Di Tenebre",
    },
}


def authority(page: int) -> dict[str, Any]:
    return {
        "page":page,"ruleset":"2014","filename":SOURCE,
        "source_role":"authority","logical_page":page+200,
        "source_title":TITLE,"source_status":"active",
        "authority_class":"licensed_translation",
        "logical_source_id":"mpmm_2022_it",
    }


def audit_wrong_neighbor(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    """Fail-closed exact state comparison before suggesting an attribute-only fix."""
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("registered_verified_source_not_found")
    s=TARGETS[name]
    expected={
        "id":s["id"],"user_id":USER,"name":name,
        "source_name":name,"normalized_name":name.casefold().replace("'", " "),
        "reference_type":"monster","review_status":"verified",
        "review_flags":[],"canonical_id":None,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":s["checksum"],
        "source_refs":[authority(page) for page in s["pages"]],
        "attributes":s["original_attrs"],
        "source_attributes":s["source_attrs"],
        "review_corrections":s["corrections"],
    }
    if any(row.get(k)!=v for k,v in expected.items()):
        raise ValueError("already_verified_record_source_or_old_stats_drift")
    text=row.get("source_full_text")
    if not isinstance(text,str) or text!=row.get("full_text"):
        raise ValueError("original_description_modified")
    if hashlib.sha256(text.encode("utf-8")).hexdigest()!=s["raw_sha"]:
        raise ValueError("original_source_checksum_mismatch")
    hp,count,sides,mod=s["dice"]
    if (count*(sides+1))//2+mod!=hp:
        raise ValueError("original_named_statblock_HP_math_failed")
    if monster_semantic_numeric_flags(s["proper_attrs"]):
        raise ValueError("unmodified_global_numeric_gate_failed")
    return {
        "status":"eligible_verified_stats_source_correction",
        "id":s["id"],"name":name,
        "wrong_neighbor":s["misattributed"],
        "original_named_box_pages":[p+200 for p in s["pages"]],
        "correct_stats":s["proper_attrs"],"raw_preserved":True,"writes":0,
    }
