"""MPMM original named-box statblocks, source-locked per imported record.

Includes pre-existing rows classified as weapon or other, some formerly
verified as non-monsters; their prior verification does not substitute for
this independent named creature source gate. This module writes nothing.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
FILE="Mostri del multiverso 101-200.pdf"
TITLE="Mordenkainen Presenta: Mostri del Multiverso"

TARGETS={
  "Duergar Maestro Della Mente": {
    "id": "ref_31dd101fa8155e4a93dce6d5337e1886",
    "page": 13,
    "type": "weapon",
    "status": "verified",
    "flags": [],
    "attrs": {
      "categoria": "Arma"
    },
    "source_attrs": {
      "categoria": "Arma"
    },
    "corr": {},
    "checksum": "28f6dbd8ef008a86c969ce87f11e9abe6a3c8c93086d70c5fdffc3d37b879f6c",
    "raw": "000176fb1293035d64ddf4275a0549158c5326d8727fd5ff194f93d880c6a6e4",
    "proposed": {
      "classe_armatura": "14 (armatura di cuoio)",
      "punti_ferita": "39 (6d8 + 12)",
      "velocita": "7,5 m"
    },
    "dice": [
      39,
      6,
      8,
      12
    ],
    "normalized": "duergar maestro della mente"
  },
  "Evanescente": {
    "id": "ref_0ec650151d645889af6fbc28ba7b64a6",
    "page": 22,
    "type": "other",
    "status": "verified",
    "flags": [],
    "attrs": {},
    "source_attrs": {},
    "corr": {},
    "checksum": "acc551f33f2d60faf78b445150e6162136390658c02b554669fc5d4429117f16",
    "raw": "027079cda01ea73ecdcf86893e1fc56e0909eccf5efe0315d25fb0eec7c8cb82",
    "proposed": {
      "classe_armatura": "14",
      "punti_ferita": "18 (4d8)",
      "velocita": "9 m"
    },
    "dice": [
      18,
      4,
      8,
      0
    ],
    "normalized": "evanescente"
  },
  "Githzerai Illuminato": {
    "id": "ref_9dfbedf142cb52fba32686c9ff53f48c",
    "page": 38,
    "type": "weapon",
    "status": "needs_review",
    "flags": [],
    "attrs": {
      "categoria": "Arma"
    },
    "source_attrs": {
      "categoria": "Arma"
    },
    "corr": {
      "_source_changed": True
    },
    "checksum": "1644217f966473f118adb278993d3bc16388c5c9a84adddf8d98085cc4e679ab",
    "raw": "2805caa7980fa0ea6aa80a3b453be84b4e7be64bf83f8bd004dca7736334a6e5",
    "proposed": {
      "classe_armatura": "18 (difesa psichica)",
      "punti_ferita": "112 (15d8 + 45)",
      "velocita": "12 m"
    },
    "dice": [
      112,
      15,
      8,
      45
    ],
    "normalized": "githzerai illuminato"
  },
  "Glasto Ligneo": {
    "id": "ref_f7d2b8356c3156f583453d944e77540d",
    "page": 39,
    "type": "other",
    "status": "needs_review",
    "flags": [
      "sezione_potenzialmente_continua"
    ],
    "attrs": {},
    "source_attrs": {},
    "corr": {},
    "checksum": "c1bced57ee8dbdcd7c3ba5405f74be40b2d4cd5930acee9fb8db148111525f77",
    "raw": "397c697e1c4f37ef95a780ff8287d44bd0b028407231c50f3054fdf8b5aabb55",
    "proposed": {
      "classe_armatura": "18 (armatura naturale, scudo)",
      "punti_ferita": "75 (10d8 + 30)",
      "velocita": "9 m, scalare 9 m"
    },
    "dice": [
      75,
      10,
      8,
      30
    ],
    "normalized": "glasto ligneo"
  },
  "Gnoll Scarnito": {
    "id": "ref_5ab9b9a8a12c5911ab79e598dfb43850",
    "page": 41,
    "type": "other",
    "status": "needs_review",
    "flags": [
      "sezione_potenzialmente_continua"
    ],
    "attrs": {},
    "source_attrs": {},
    "corr": {
      "_source_changed": True
    },
    "checksum": "8eb53115ee25de0ccf4d736f5d06434cb19b2f46ab94e412b288bad63cb94fab",
    "raw": "91174d0e7e8bc65869bd059ddd53e02ffeffba100969e81804b5703f929e485e",
    "proposed": {
      "classe_armatura": "12 (armatura naturale)",
      "punti_ferita": "11 (2d8 + 2)",
      "velocita": "9 m"
    },
    "dice": [
      11,
      2,
      8,
      2
    ],
    "normalized": "gnoll scarnito"
  },
  "Guardia Nera": {
    "id": "ref_190949e659915cc9a5e57e8551251c5d",
    "page": 46,
    "type": "other",
    "status": "verified",
    "flags": [],
    "attrs": {},
    "source_attrs": {},
    "corr": {},
    "checksum": "e2cc180ba1fa53cc04999630b8972dc367f8a3153e3bec41246bbefeef363bd5",
    "raw": "9107f5876e0434a80179f2d23798de7b8f68c77e118aba6d068a7007ce63cd82",
    "proposed": {
      "classe_armatura": "18 (piastre)",
      "punti_ferita": "119 (14d8 + 56)",
      "velocita": "9 m"
    },
    "dice": [
      119,
      14,
      8,
      56
    ],
    "normalized": "guardia nera"
  },
  "Inseguitore Strisciante": {
    "id": "ref_15e78a735b275aa48270e7e8b4c9b426",
    "page": 53,
    "type": "other",
    "status": "needs_review",
    "flags": [
      "sezione_potenzialmente_continua"
    ],
    "attrs": {},
    "source_attrs": {},
    "corr": {
      "_source_changed": True
    },
    "checksum": "bfc7aa8ce3b0fc275278c3fdaa94e53d293cc478a84410264a6535d38a559fdd",
    "raw": "d0e75a8daf04d340b1410f9753efc5a68328acdd0ae57c55f93bc07ea10446d7",
    "proposed": {
      "classe_armatura": "14",
      "punti_ferita": "39 (6d8 + 12)",
      "velocita": "9 m, scalare 9 m"
    },
    "dice": [
      39,
      6,
      8,
      12
    ],
    "normalized": "inseguitore strisciante"
  },
  "Kruthik Adulto": {
    "id": "ref_5bcc6c634c935ab3acc8156f4cf845a0",
    "page": 61,
    "type": "other",
    "status": "needs_review",
    "flags": [],
    "attrs": {},
    "source_attrs": {},
    "corr": {
      "_source_changed": True
    },
    "checksum": "0f739ca3a7494f8ac0e6139552cb82a9a7d9dea31b6c50383e15009db9e3ce3b",
    "raw": "f27bd18c2e600acc6cb75a45b2bdc05f23942c803adbdc81f59e33da8005fc5e",
    "proposed": {
      "classe_armatura": "18 (armatura naturale)",
      "punti_ferita": "39 (6d8 + 12)",
      "velocita": "12 m, scavare 6 m, scalare 12 m"
    },
    "dice": [
      39,
      6,
      8,
      12
    ],
    "normalized": "kruthik adulto"
  },
  "Lavamandra Guerriera": {
    "id": "ref_2a95f83f249057d4953d83e469d0717b",
    "page": 64,
    "type": "other",
    "status": "needs_review",
    "flags": [],
    "attrs": {},
    "source_attrs": {},
    "corr": {
      "_source_changed": True
    },
    "checksum": "0f16c9886edbbc6855d3db08b497d5aff5a6dc97a360d936c2d774f15c6ce17c",
    "raw": "6ef5992792dce67e734e9bb43534cbc4b691759ce947a953a7e22edc277f8e16",
    "proposed": {
      "classe_armatura": "13 (scudo)",
      "punti_ferita": "27 (5d8 + 5)",
      "velocita": "9 m"
    },
    "dice": [
      27,
      5,
      8,
      5
    ],
    "normalized": "lavamandra guerriera"
  },
  "Mastino D'Ombra": {
    "id": "ref_4537518342a1557e80bd71d92191b0f7",
    "page": 76,
    "type": "other",
    "status": "needs_review",
    "flags": [],
    "attrs": {},
    "source_attrs": {},
    "corr": {
      "_source_changed": True
    },
    "checksum": "afd1c45b70aec6425ac5f52fde674453c42e56148b14106fe11511c70d888db0",
    "raw": "0c2b6447fc9d2330dcb8d978e5297526a1761fb70ad82d6c1078a1599cce356e",
    "proposed": {
      "classe_armatura": "12",
      "punti_ferita": "33 (6d8 + 6)",
      "velocita": "12 m"
    },
    "dice": [
      33,
      6,
      8,
      6
    ],
    "normalized": "mastino d ombra"
  },
  "Maurezhi": {
    "id": "ref_fa06ca27547a5c1383d0cb05d1e04686",
    "page": 77,
    "type": "other",
    "status": "needs_review",
    "flags": [
      "sezione_potenzialmente_continua"
    ],
    "attrs": {},
    "source_attrs": {},
    "corr": {
      "_source_changed": True
    },
    "checksum": "628dcaa99bcbb363ff6ace34cfaa54b1c04234f40b333f253f249f1e679d08cb",
    "raw": "e67b230599024215e62b51d5557e1deb6efa3b7188567b84c5e4eb4474556af9",
    "proposed": {
      "classe_armatura": "15 (armatura naturale)",
      "punti_ferita": "88 (16d8 + 16)",
      "velocita": "9 m"
    },
    "dice": [
      88,
      16,
      8,
      16
    ],
    "normalized": "maurezhi"
  },
  "Nagpa": {
    "id": "ref_dae0d354804259b88bd0d872a32885c3",
    "page": 96,
    "type": "other",
    "status": "needs_review",
    "flags": [],
    "attrs": {},
    "source_attrs": {},
    "corr": {
      "_source_changed": True
    },
    "checksum": "ebbbae662ce7729063f1b47009ec3e4a7cb8f2cee963965e6328f6c3f94cb043",
    "raw": "451c4dcc434489aa094899032a75cf94a9899bbcdbefe02a4e50c50f6ec75e83",
    "proposed": {
      "classe_armatura": "19 (armatura naturale)",
      "punti_ferita": "203 (37d8 + 37)",
      "velocita": "9 m"
    },
    "dice": [
      203,
      37,
      8,
      37
    ],
    "normalized": "nagpa"
  }
}


def authority(page:int)->dict[str,Any]:
    return {
      "page":page,"ruleset":"2014","filename":FILE,
      "source_role":"authority","logical_page":page+100,
      "source_title":TITLE,"source_status":"active",
      "authority_class":"licensed_translation",
      "logical_source_id":"mpmm_2022_it",
    }


def audit_existing_monster(name:str, row:dict[str,Any]|None)->dict[str,Any]:
    """Independent exact-snapshot fail-closed named creature audit."""
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("missing_source_candidate")
    t=TARGETS[name]
    before={
        "id":t["id"],"name":name,"source_name":name,
        "normalized_name":t["normalized"],"user_id":OWNER,
        "reference_type":t["type"],"review_status":t["status"],
        "review_flags":t["flags"],"canonical_id":None,
        "source_key":FILE,"source_language":"it",
        "source_text_checksum":t["checksum"],
        "attributes":t["attrs"],"source_attributes":t["source_attrs"],
        "review_corrections":t["corr"],
        "source_refs":[authority(t["page"])],
    }
    if any(row.get(k)!=value for k,value in before.items()):
        raise ValueError("original_registered_record_drift")
    raw=row.get("full_text")
    if not isinstance(raw,str) or raw!=row.get("source_full_text"):
        raise ValueError("original_source_raw_modified")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=t["raw"]:
        raise ValueError("historical_source_raw_sha256_changed")
    hp,num,sides,bonus=t["dice"]
    if num*(sides+1)//2+bonus!=hp:
        raise ValueError("original_boxed_hit_dice_average_mismatch")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(t["proposed"]):
        raise ValueError("strict_global_semantic_gate_failed")
    return {
        "status":"eligible_independent_source_monster_review",
        "name":name,"id":t["id"],"original_review_status":t["status"],
        "source_page":t["page"]+100,"proposed_attributes":t["proposed"],
        "historical_source_preserved":True,"writes":0,
    }
