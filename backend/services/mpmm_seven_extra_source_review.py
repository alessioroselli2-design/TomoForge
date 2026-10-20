"""Seven original MPMM named creature boxes across two licensed PDF parts.

Source references are immutable, including Hutijin whose narrative begins
on physical page 50 and whose named CA/HP/speed box occupies page 51.
Strict exact source audit and math gates; zero writes.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

OWNER="user_fabf28726a20"
TITLE="Mordenkainen Presenta: Mostri del Multiverso"
TARGETS={
  "Hutijin": {
    "id": "ref_ec7dcbd309c8553e8acef69dd2dcbd00",
    "part": "101-200",
    "page": 50,
    "box": 51,
    "type": "other",
    "status": "verified",
    "flags": [],
    "corr": {},
    "checksum": "12ce44512914a4e95e0a0586e54407e0cd70010cd212a248a5527b3a7cdf4468",
    "raw": "b357549eb31421f3e14c75832540a426fc1552499797a594afafdfa1f31c4773",
    "dice": [
      200,
      16,
      10,
      112
    ],
    "stats": {
      "classe_armatura": "19 (armatura naturale)",
      "punti_ferita": "200 (16d10 + 112)",
      "velocita": "9 m, volare 18 m"
    }
  },
  "Ladro Esperto": {
    "id": "ref_01a4589c392257cdb7c54ae68a5ff472",
    "part": "101-200",
    "page": 63,
    "box": 63,
    "type": "other",
    "status": "verified",
    "flags": [],
    "corr": {},
    "checksum": "3b1a59716a1707ab0f67acd6f4d5cce1a9241221377be453238388b05185088e",
    "raw": "0b36d1cfbf08a5cce16b678a067e4655b81e7ffcf93b92794be3141f8658eec3",
    "dice": [
      84,
      13,
      8,
      26
    ],
    "stats": {
      "classe_armatura": "16 (cuoio borchiato)",
      "punti_ferita": "84 (13d8 + 26)",
      "velocita": "9 m"
    }
  },
  "Meenlock": {
    "id": "ref_268341052b665d11ac5238b119cb3007",
    "part": "101-200",
    "page": 82,
    "box": 82,
    "type": "other",
    "status": "verified",
    "flags": [],
    "corr": {},
    "checksum": "6fa5059463318138c17ea4e51e059bca80175fc08e54ce16e95208d99267bd66",
    "raw": "f1ff6e0a03187b6335d28a9f2aefdc7d431c6c86b8073ed1ea9f677a273f242a",
    "dice": [
      31,
      7,
      6,
      7
    ],
    "stats": {
      "classe_armatura": "15 (armatura naturale)",
      "punti_ferita": "31 (7d6 + 7)",
      "velocita": "9 m"
    }
  },
  "Megera Annis": {
    "id": "ref_f5716e88c25554a78fc68df45cc75ece",
    "part": "101-200",
    "page": 83,
    "box": 83,
    "type": "other",
    "status": "verified",
    "flags": [],
    "corr": {},
    "checksum": "8977078c3babbf0a443586c9308d68282c9a10680a8b1e001d92020a2bef8afe",
    "raw": "fa40f9ab856895ee0bf76dce72ad20ce6940c2269973f8fd3dcf8fd5c9c0cb7f",
    "dice": [
      90,
      12,
      10,
      24
    ],
    "stats": {
      "classe_armatura": "17 (armatura naturale)",
      "punti_ferita": "90 (12d10 + 24)",
      "velocita": "12 m"
    }
  },
  "Merregon": {
    "id": "ref_d8daf362eeab5a85b2b4b618950e8e4b",
    "part": "101-200",
    "page": 85,
    "box": 85,
    "type": "other",
    "status": "verified",
    "flags": [],
    "corr": {},
    "checksum": "9a6c4d2ceb87b17b1f2dd789ad7f1caee7368f3d868784b176781dfd22ca217c",
    "raw": "e74629e5dc5de07a1937189a265fd09ff190b217d6e050c0104a5e6bf69544d3",
    "dice": [
      45,
      6,
      8,
      18
    ],
    "stats": {
      "classe_armatura": "16 (armatura naturale)",
      "punti_ferita": "45 (6d8 + 18)",
      "velocita": "9 m"
    }
  },
  "Molydeus": {
    "id": "ref_c199f7e5f23d559abbfcb59280c7762f",
    "part": "101-200",
    "page": 91,
    "box": 91,
    "type": "ability",
    "status": "verified",
    "flags": [],
    "corr": {},
    "checksum": "14be91520a6e6ca7536458140a38f6597f9ee88d3a49a2d7e0c4347bd62dd175",
    "raw": "ef4d63f28c1685924af2188deb482ae9efafb8b4eafa3215428b5587283fbb71",
    "dice": [
      216,
      16,
      12,
      112
    ],
    "stats": {
      "classe_armatura": "19 (armatura naturale)",
      "punti_ferita": "216 (16d12 + 112)",
      "velocita": "12 m"
    }
  },
  "Yagnoloth": {
    "id": "ref_8ca7c91e877e5690a7a09358e74ce418",
    "part": "201-294",
    "page": 72,
    "box": 72,
    "type": "other",
    "status": "needs_review",
    "flags": [],
    "corr": {
      "_source_changed": True
    },
    "checksum": "1dbe5f699db96926536ee041bdcea40deea5570e3abd3a72f258cb577e686a96",
    "raw": "d3eb7c299bcf8f2cac16a051b4f56d4f30c7cc6b277215b64e1212cea84019da",
    "dice": [
      147,
      14,
      10,
      70
    ],
    "stats": {
      "classe_armatura": "17 (armatura naturale)",
      "punti_ferita": "147 (14d10 + 70)",
      "velocita": "12 m"
    }
  }
}

def part_filename(part:str)->str:
    return "Mostri del multiverso "+part+".pdf"

def authority(t:dict[str,Any])->dict[str,Any]:
    offset=100 if t["part"]=="101-200" else 200
    return {
        "page":t["page"],"ruleset":"2014",
        "filename":part_filename(t["part"]),"source_role":"authority",
        "logical_page":t["page"]+offset,
        "source_title":TITLE,"source_status":"active",
        "authority_class":"licensed_translation",
        "logical_source_id":"mpmm_2022_it",
    }

def source_audit(name:str,row:dict[str,Any]|None)->dict[str,Any]:
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("original_registered_monster_missing")
    t=TARGETS[name]
    required={
        "id":t["id"],"user_id":OWNER,"name":name,
        "source_name":name,"normalized_name":name.casefold(),
        "reference_type":t["type"],"review_status":t["status"],
        "review_flags":t["flags"],"canonical_id":None,
        "source_key":part_filename(t["part"]),"source_language":"it",
        "source_text_checksum":t["checksum"],
        "source_refs":[authority(t)],"attributes":{},
        "source_attributes":{},"review_corrections":t["corr"],
    }
    if any(row.get(k)!=v for k,v in required.items()):
        raise ValueError("registered_licensed_source_snapshot_drift")
    full=row.get("full_text")
    if not isinstance(full,str) or full!=row.get("source_full_text"):
        raise ValueError("historical_raw_evidence_modified")
    if hashlib.sha256(full.encode("utf-8")).hexdigest()!=t["raw"]:
        raise ValueError("exact_source_sha256_drift")
    hp,n,faces,b=t["dice"]
    if n*(faces+1)//2+b!=hp:
        raise ValueError("original_hit_dice_math_incoherent")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(t["stats"]):
        raise ValueError("unchanged_global_numeric_or_identity_gate_failed")
    if name=="Hutijin" and (t["page"]!=50 or t["box"]!=51):
        raise ValueError("Hutijin_narrative_to_box_page_discrepancy_not_explicit")
    return {"status":"eligible_original_independent_boxed_monster",
            "id":t["id"],"name":name,
            "registered_page":t["page"],
            "physical_statblock_page":t["box"],
            "stats":t["stats"],"writes":0,"raw_source_preserved":True}
