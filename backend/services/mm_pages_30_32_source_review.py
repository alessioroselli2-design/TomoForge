"""Read-only original source audit for four distinct MM p30–32 statblocks.

The user's licensed Italian source PDF 353 pages is stored privately.
The title Bugbear on p32 is a section heading *plus two separate creatures*:
Bugbear and Bugbear Capotribù. Both must be uniquely identified.
Only concise source-confirmed core fields are sealed; no DB writes.
"""
from __future__ import annotations
import hashlib
import re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import (
    monster_identity_sanity_flags, monster_semantic_numeric_flags,
)

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES = 353
MONSTERS = {
  "Spettatore": {
    "id": "ref_33a8d9d2d8704ffaa5ccaad64164088a",
    "page": 30,
    "kind": "Aberrazione Media",
    "type": "Aberrazione",
    "size": "Media",
    "align": "legale neutrale",
    "ac": "14 (armatura naturale)",
    "hp": "39 (6d8 + 12)",
    "speed": "0 m, volare 9 m (fluttuare)",
    "gs": "3",
    "abilities": {
      "for": "8",
      "des": "14",
      "cos": "14",
      "int": "13",
      "sag": "14",
      "car": "11"
    },
    "excerpt_sha": "688db47f22d9d319a69401462cc445622a194ed28aa39c7aff07337a817c4782"
  },
  "Belva Distorcente": {
    "id": "ref_e4e69058eb282b07fec7f5cf859c814f",
    "page": 31,
    "kind": "Mostruosità Grande",
    "type": "Mostruosità",
    "size": "Grande",
    "align": "legale malvagio",
    "ac": "13 (armatura naturale)",
    "hp": "85 (10d10 + 30)",
    "speed": "12 m",
    "gs": "3",
    "abilities": {
      "for": "18",
      "des": "15",
      "cos": "16",
      "int": "6",
      "sag": "12",
      "car": "8"
    },
    "excerpt_sha": "0765e7f784eca9eabda2874eddb8ce87ce4428a75f75f1200e3d74da1b301389"
  },
  "Bugbear": {
    "id": "ref_fd153302b178c5d60b7abdda15089a53",
    "page": 32,
    "kind": "Umanoide Medio (goblinoide)",
    "type": "Umanoide",
    "size": "Medio",
    "align": "caotico malvagio",
    "ac": "16 (armatura di pelle, scudo)",
    "hp": "27 (5d8 + 5)",
    "speed": "9 m",
    "gs": "1",
    "abilities": {
      "for": "15",
      "des": "14",
      "cos": "13",
      "int": "8",
      "sag": "11",
      "car": "9"
    },
    "excerpt_sha": "e770e9c70c70206740dcf1fa99dd3e2958336eef0c4b298105b34f442e18d08e"
  },
  "Bugbear Capotribù": {
    "id": "ref_7c30bb1a4f5f6bb65755baa1be57a98d",
    "page": 32,
    "kind": "Umanoide Medio (goblinoide)",
    "type": "Umanoide",
    "size": "Medio",
    "align": "caotico malvagio",
    "ac": "17 (giaco di maglia, scudo)",
    "hp": "65 (10d8 + 20)",
    "speed": "9 m",
    "gs": "3",
    "abilities": {
      "for": "17",
      "des": "14",
      "cos": "14",
      "int": "11",
      "sag": "12",
      "car": "11"
    },
    "excerpt_sha": "3f31a41e31296340e39b2a87e352a7d225f35e633f037f56d50e4b5e8f038de8"
  }
}
HP = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")


def excerpt(name: str, block: dict[str, Any]) -> str:
    return (
        f"{name}. {block['kind']}, {block['align']}. "
        f"Classe Armatura {block['ac']}. Punti Ferita {block['hp']}. "
        f"Velocità {block['speed']}. Sfida {block['gs']}."
    )


def audit(name: str, catalog: dict[str, Any] | None,
          monster_id_present: bool, monster_names_present: list) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unexpected_monster")
    if monster_id_present or monster_names_present:
        raise ValueError("duplicate_monster")
    required = {
        "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
        "physical_sha256":SHA256,"physical_pages":PAGES,
        "source_role":"authority","source_status":"active",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(k) != v for k, v in required.items()
    ):
        raise ValueError("registered_source_mismatch")
    block = MONSTERS[name]
    if block["page"] not in (30,31,32):
        raise ValueError("wrong_original_page")
    token = f"{SOURCE_ID}|{FILENAME}|{block['page']}|{name.casefold()}"
    expected_id = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if expected_id != block["id"]:
        raise ValueError("source_id_changed")
    source = excerpt(name, block)
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != block["excerpt_sha"]:
        raise ValueError("sealed_original_facts_changed")
    data = {
        "classe_armatura":block["ac"], "punti_ferita":block["hp"],
        "velocita":block["speed"],"grado_sfida":block["gs"],
        "caratteristiche":block["abilities"],"tipo_creatura":block["type"],
        "taglia":block["size"],"allineamento":block["align"],
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(data):
        raise ValueError("identity_or_numeric_gate")
    matched = HP.fullmatch(block["hp"])
    if not matched:
        raise ValueError("hit_dice_format")
    avg,count,faces,bonus = matched.groups()
    if int(avg) != int(count) * (int(faces)+1)//2+int(bonus or 0):
        raise ValueError("hit_dice_math")
    if set(block["abilities"]) != {"for","des","cos","int","sag","car"} or any(
        not 1 <= int(n) <= 30 for n in block["abilities"].values()
    ):
        raise ValueError("missing_abilities")
    return {
        "id":expected_id,"name":name,"page":block["page"],
        "source_excerpt":source,"source_text_checksum":digest,
        "attributes":deepcopy(data), "writes":0,
    }
