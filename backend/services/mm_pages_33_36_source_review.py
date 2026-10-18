"""Read-only source proof for four Italian Monster Manual blocks, pages 33–36.

Full-file SHA-256 checked against original owner-supplied scan (353 pages).
Core data visually checked, source identities locked, no automated promotion.
"""
from __future__ import annotations
import hashlib
import re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import (
    monster_identity_sanity_flags, monster_semantic_numeric_flags,
)

FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SOURCE_ID = "mm_2014_it"
SHA = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
NUM_PAGES = 353
MONSTERS = {
  "Bulette": {
    "id": "ref_5b6527c448a0afbbe3a32fd663312675",
    "page": 33,
    "kind": "Mostruosità Grande",
    "type": "Mostruosità",
    "size": "Grande",
    "align": "senza allineamento",
    "ac": "17 (armatura naturale)",
    "hp": "94 (9d10 + 45)",
    "speed": "12 m, scavare 12 m",
    "gs": "5",
    "abilities": {
      "for": "19",
      "des": "11",
      "cos": "21",
      "int": "2",
      "sag": "10",
      "car": "5"
    },
    "sha": "db0db454b5ab55401ae2968e409f3d6290118f2eac2ff19cb4c5ba7b1436672f"
  },
  "Bullywug": {
    "id": "ref_1f0a5a00fc3e4c160163896347554aa1",
    "page": 34,
    "kind": "Umanoide Medio (bullywug)",
    "type": "Umanoide",
    "size": "Medio",
    "align": "neutrale malvagio",
    "ac": "15 (armatura di pelle, scudo)",
    "hp": "11 (2d8 + 2)",
    "speed": "6 m, nuotare 12 m",
    "gs": "1/4",
    "abilities": {
      "for": "12",
      "des": "12",
      "cos": "13",
      "int": "7",
      "sag": "10",
      "car": "7"
    },
    "sha": "9a93951d29d792577185fc606a940f9dd7477fa55f8c0a86f5cde214d4db1231"
  },
  "Cacciatore Invisibile": {
    "id": "ref_ebe3e1e7e9997061c188eae600882fec",
    "page": 35,
    "kind": "Elementale Medio",
    "type": "Elementale",
    "size": "Medio",
    "align": "neutrale",
    "ac": "14",
    "hp": "104 (16d8 + 32)",
    "speed": "15 m, volare 15 m (fluttuare)",
    "gs": "6",
    "abilities": {
      "for": "16",
      "des": "19",
      "cos": "14",
      "int": "10",
      "sag": "15",
      "car": "11"
    },
    "sha": "913ae2805af9a60e031fb2397466f18709660b09fca45c8426ff12bfff60da8c"
  },
  "Cambion": {
    "id": "ref_b5f849bf9bd7968749207e2e8993fb43",
    "page": 36,
    "kind": "Immondo Medio",
    "type": "Immondo",
    "size": "Medio",
    "align": "qualsiasi allineamento malvagio",
    "ac": "19 (corazza di scaglie)",
    "hp": "82 (11d8 + 33)",
    "speed": "9 m, volare 18 m",
    "gs": "5",
    "abilities": {
      "for": "18",
      "des": "18",
      "cos": "16",
      "int": "14",
      "sag": "12",
      "car": "16"
    },
    "sha": "9ade7ff099f8455cc52885eca853bd791088123d30744d1882bb865e90c5bbaa"
  }
}
HP_EXPR = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")


def concise_source(name: str, block: dict[str, Any]) -> str:
    return (
        f"{name}. {block['kind']}, {block['align']}. "
        f"Classe Armatura {block['ac']}. Punti Ferita {block['hp']}. "
        f"Velocità {block['speed']}. Sfida {block['gs']}."
    )


def audit(name: str, source: dict[str, Any] | None,
          duplicate_id: bool, duplicate_monster_names: list) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unknown_original_statblock")
    if duplicate_id or duplicate_monster_names:
        raise ValueError("monster_collision")
    required = {
        "logical_source_id":SOURCE_ID,
        "physical_filename":FILENAME,
        "physical_sha256":SHA,
        "physical_pages":NUM_PAGES,
        "source_status":"active",
        "source_role":"authority",
        "authority_class":"licensed_translation",
        "text_mode":"vision_required",
    }
    if not isinstance(source, dict) or any(
        source.get(k) != v for k, v in required.items()
    ):
        raise ValueError("registered_source_changed")
    d = MONSTERS[name]
    if d["page"] not in (33,34,35,36):
        raise ValueError("physical_page_wrong")
    expected_id = "ref_" + hashlib.sha256(
        f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}".encode()
    ).hexdigest()[:32]
    if d["id"] != expected_id:
        raise ValueError("source_id_drift")
    brief = concise_source(name, d)
    brief_sha = hashlib.sha256(brief.encode()).hexdigest()
    if brief_sha != d["sha"]:
        raise ValueError("source_core_checksum_changed")
    attrs = {
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],"velocita":d["speed"],
        "grado_sfida":d["gs"],"caratteristiche":d["abilities"],
        "tipo_creatura":d["type"],"taglia":d["size"],"allineamento":d["align"],
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_monster_semantic_gate")
    match = HP_EXPR.fullmatch(d["hp"])
    if not match:
        raise ValueError("invalid_hp_expression")
    avg,count,faces,modifier=match.groups()
    if int(avg) != int(count)*(int(faces)+1)//2+int(modifier or 0):
        raise ValueError("hp_dice_average_mismatch")
    if set(d["abilities"]) != {"for","des","cos","int","sag","car"} or any(
        not 1<=int(x)<=30 for x in d["abilities"].values()
    ):
        raise ValueError("six_ability_scores_invalid")
    return {"id":expected_id,"name":name,"page":d["page"],"attributes":deepcopy(attrs),
            "source_excerpt":brief,"source_text_checksum":brief_sha,"writes":0}
