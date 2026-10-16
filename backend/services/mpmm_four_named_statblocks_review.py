"""Original Italian MPMM named-statblock audit for four misclassified creatures.

Read only. Each original imported source is immutable; only a later guarded
transaction may change the displayed classification after full checks.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
FILE="Mostri del multiverso 201-294.pdf"
TITLE="Mordenkainen Presenta: Mostri del Multiverso"
TARGETS={
    "Somiero Gigante": {
        "id": "ref_4d118233f6ec526f9fce6752d80a0015",
        "page": 47,
        "type": "other",
        "flag": [
            "sezione_potenzialmente_continua"
        ],
        "checksum": "6a1f8ddcebb711674c1ab383da91617706acef376f9bd6c3737627c417d29ae6",
        "raw": "7d248ab550a1216f1cfbeb1d76e628e91a9f44892b23d42b77fb3c24b23b8b32",
        "corr": {},
        "attrs": {
            "classe_armatura": "14 (armatura naturale)",
            "punti_ferita": "22 (3d10 + 6)",
            "velocita": "15 m"
        },
        "dice": [
            22,
            3,
            10,
            6
        ]
    },
    "Terrore Gigante Di Fuoco": {
        "id": "ref_e870c9a40ffa5c39b9fee58513a3e7b5",
        "page": 53,
        "type": "other",
        "flag": [
            "sezione_potenzialmente_continua"
        ],
        "checksum": "0af5e54731c5ad3c2568ec99a4d7e5505deeaf671f8ea2289997f4314ebdf1a2",
        "raw": "5763ef753e3c93a5add9a70f6fd63485b077f0a5097ecfeb79236ad694b3618f",
        "corr": {
            "_source_changed": True
        },
        "attrs": {
            "classe_armatura": "21 (piastre, duplice scudo)",
            "punti_ferita": "187 (15d12 + 90)",
            "velocita": "9 m"
        },
        "dice": [
            187,
            15,
            12,
            90
        ]
    },
    "Venator": {
        "id": "ref_dc9a60dbe52a5ebf9310495c61e60fae",
        "page": 67,
        "type": "ability",
        "flag": [],
        "checksum": "a1a9870c756485e233098f731bf1b110dec577ea8f8b7443a70dcf3df39c2b05",
        "raw": "beebd819a226887e78f9c8bbad9a728b7526b37b32b291e0d06a769b19b7d1a2",
        "corr": {
            "_source_changed": True
        },
        "attrs": {
            "classe_armatura": "13 (armatura naturale)",
            "punti_ferita": "68 (8d10 + 24)",
            "velocita": "6 m, scalare 6 m"
        },
        "dice": [
            68,
            8,
            10,
            24
        ]
    },
    "Yagnoloth": {
        "id": "ref_8ca7c91e877e5690a7a09358e74ce418",
        "page": 72,
        "type": "other",
        "flag": [],
        "checksum": "1dbe5f699db96926536ee041bdcea40deea5570e3abd3a72f258cb577e686a96",
        "raw": "d3eb7c299bcf8f2cac16a051b4f56d4f30c7cc6b277215b64e1212cea84019da",
        "corr": {
            "_source_changed": True
        },
        "attrs": {
            "classe_armatura": "17 (armatura naturale)",
            "punti_ferita": "147 (14d10 + 70)",
            "velocita": "12 m"
        },
        "dice": [
            147,
            14,
            10,
            70
        ]
    }
}

def authority(p: int) -> dict[str, Any]:
    return {"page":p,"ruleset":"2014","filename":FILE,
      "source_role":"authority","logical_page":p+200,"source_title":TITLE,
      "source_status":"active","authority_class":"licensed_translation",
      "logical_source_id":"mpmm_2022_it"}

def validate_record(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("registered_original_record_missing")
    t=TARGETS[name]
    expected={
        "id":t["id"],"user_id":OWNER,"name":name,"source_name":name,
        "normalized_name":name.casefold(),"reference_type":t["type"],
        "review_status":"needs_review","review_flags":t["flag"],
        "canonical_id":None,"source_key":FILE,"source_language":"it",
        "source_text_checksum":t["checksum"],"source_refs":[authority(t["page"])],
        "attributes":{},"source_attributes":{},"review_corrections":t["corr"],
    }
    if any(row.get(k)!=v for k,v in expected.items()):
        raise ValueError("original_source_row_snapshot_drift")
    raw=row.get("full_text")
    if not isinstance(raw,str) or raw!=row.get("source_full_text"):
        raise ValueError("original_registered_raw_description_modified")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=t["raw"]:
        raise ValueError("source_full_text_sha256_drift")
    hp,n,sides,bonus=t["dice"]
    if n*(sides+1)//2+bonus!=hp:
        raise ValueError("independent_original_hp_math_incoherent")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(t["attrs"]):
        raise ValueError("global_semantic_gate_rejects_proposed_stats")
    return {
        "status":"eligible_exact_original_source_reclassification",
        "name":name,"id":t["id"],"logical_page":t["page"]+200,
        "attributes":t["attrs"],"original_type":t["type"],
        "historical_flags":t["flag"],"no_writes":True,"writes":0,
    }
