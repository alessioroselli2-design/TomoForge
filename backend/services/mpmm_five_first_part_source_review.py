"""Read-only source seal: five first-part MPMM boxed monsters misclassified.

Earlier other/verified or class/verified state describes the old category,
not a verified monster. The independently named original statblock must be
certified before the record becomes monster/verified.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
FILE="Mostri del multi verso 1-100.pdf"
TITLE="Mordenkainen Presenta: Mostri del Multiverso"
TARGETS={
  "Amnizu": {
    "id": "ref_c773a569872e5e96a209d1cb9682c9df",
    "page": 53,
    "type": "other",
    "checksum": "40167904715cf2a5517f41d7a06df969ef7f853675c8e642234e5a5cb99791ae",
    "raw": "5aadcd3224866cf469ac61b9b6a94435ed6c62c599d7c2b7ebed011e5926979e",
    "proposed": {
      "classe_armatura": "21 (armatura naturale)",
      "punti_ferita": "202 (27d8 + 81)",
      "velocita": "9 m, volare 12 m"
    },
    "dice": [
      202,
      27,
      8,
      81
    ]
  },
  "Arcidruido": {
    "id": "ref_fadd98159cb95ae3bc7a1c48b3724e6c",
    "page": 54,
    "type": "other",
    "checksum": "145632ff55d85e31b90c0703c042e77ce105eb071718e2583ec96381b26ddab6",
    "raw": "77ca957f8ba6c02711d7729ab710b499cb60f26190763c261d327371a8c5dc98",
    "proposed": {
      "classe_armatura": "14 (armatura di pelle)",
      "punti_ferita": "154 (28d8 + 28)",
      "velocita": "9 m"
    },
    "dice": [
      154,
      28,
      8,
      28
    ]
  },
  "Bacio Della Morte": {
    "id": "ref_5f2cb6c93efc52ee93321ec5bab27cdc",
    "page": 59,
    "type": "other",
    "checksum": "92387ad421276e393b06c2ea8c662c8b7d2775f8212f4b627ab865a5a1d04fae",
    "raw": "12ef489b445acbc2dafaecce5ad46a09782eb30356c4b54e60b8df0e841c0fbe",
    "proposed": {
      "classe_armatura": "15 (armatura naturale)",
      "punti_ferita": "142 (15d10 + 60)",
      "velocita": "0 m, volare 9 m (fluttuare)"
    },
    "dice": [
      142,
      15,
      10,
      60
    ]
  },
  "Bardo": {
    "id": "ref_23f704804c1059e4becdde28c0b01061",
    "page": 66,
    "type": "class",
    "checksum": "05e4578077a78782da4259ea1ed8bc563e17055a98ffb609f741eacfc02f016b",
    "raw": "95239fe4c61d282d82e10a69edc784b3419e2883075fc6fef633c071b72a6111",
    "proposed": {
      "classe_armatura": "15 (giaco di maglia)",
      "punti_ferita": "44 (8d8 + 8)",
      "velocita": "9 m"
    },
    "dice": [
      44,
      8,
      8,
      8
    ]
  },
  "Chitinide": {
    "id": "ref_903c5cfe0459571db2932459217a85c0",
    "page": 83,
    "type": "other",
    "checksum": "60d4074076f24be513770a2613964870752fd7db8780dde245bbc1c32698d144",
    "raw": "8e238430d4b5ade17baac94543a8f44f5d1318c938212686733a9e7febb447eb",
    "proposed": {
      "classe_armatura": "14 (armatura di pelle)",
      "punti_ferita": "18 (4d6 + 4)",
      "velocita": "9 m, scalare 9 m"
    },
    "dice": [
      18,
      4,
      6,
      4
    ]
  }
}

def authority(pg:int)->dict[str,Any]:
    return {"page":pg,"ruleset":"2014","filename":FILE,
            "source_role":"authority","logical_page":pg,
            "source_title":TITLE,"source_status":"active",
            "authority_class":"licensed_translation",
            "logical_source_id":"mpmm_2022_it"}

def inspect_monster(name:str,original:dict[str,Any]|None)->dict[str,Any]:
    if name not in TARGETS or not isinstance(original,dict):
        raise ValueError("original_licensed_candidate_missing")
    t=TARGETS[name]
    guard={
        "id":t["id"],"name":name,"source_name":name,
        "normalized_name":name.casefold(),"user_id":OWNER,
        "reference_type":t["type"],"review_status":"verified",
        "review_flags":[],"canonical_id":None,
        "source_key":FILE,"source_language":"it",
        "source_text_checksum":t["checksum"],
        "source_refs":[authority(t["page"])],
        "attributes":{},"source_attributes":{},"review_corrections":{},
    }
    if any(original.get(k)!=v for k,v in guard.items()):
        raise ValueError("original_imported_source_snapshot_drift")
    raw=original.get("full_text")
    if not isinstance(raw,str) or raw!=original.get("source_full_text"):
        raise ValueError("registered_original_text_not_preserved")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=t["raw"]:
        raise ValueError("registered_original_SHA256_drift")
    hp,n,d,b=t["dice"]
    if n*(d+1)//2+b!=hp:
        raise ValueError("source_boxed_hit_dice_average_incoherent")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(t["proposed"]):
        raise ValueError("global_source_semantic_numeric_gate_rejected")
    return {
        "status":"eligible_original_independent_boxed_monster",
        "name":name,"id":t["id"],"logical_page":t["page"],
        "original_reference_type":t["type"],
        "stats":t["proposed"],"writes":0,
    }
