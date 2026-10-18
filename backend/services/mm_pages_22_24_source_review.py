"""Source-only audit gates for MM p22-24: Azer, Banshee and Basilisco.

Source is the user's licensed Italian PDF, 353 physical pages, checked against the
registered whole-file digest. The source remains private. Only manually confirmed
short statblock facts are sealed here, never full copyrighted page scans.
"""
from __future__ import annotations
import hashlib
import re
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import (
    monster_identity_sanity_flags,
    monster_semantic_numeric_flags,
)

SOURCE_ID = "mm_2014_it"
SOURCE_FILE = "847921086-Manuale-Dei-Mostri-5e.pdf"
SOURCE_SHA = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
SOURCE_PAGES = 353
DICE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")
MONSTERS = {
  "Azer": {
    "name": "Azer",
    "id": "ref_6081a1f5ee2a740c571c7a87fd76b9a9",
    "page": 22,
    "kind": "Elementale Medio",
    "type": "Elementale",
    "size": "Medio",
    "align": "legale neutrale",
    "ac": "17 (armatura naturale, scudo)",
    "hp": "39 (6d8 + 12)",
    "speed": "9 m",
    "gs": "2",
    "abilities": {
      "for": "17",
      "des": "12",
      "cos": "15",
      "int": "12",
      "sag": "13",
      "car": "10"
    },
    "excerpt_sha": "63791b0ef87dde843180260d3d45f1b38ad68c4f28060de0c2674a67a2617168"
  },
  "Banshee": {
    "name": "Banshee",
    "id": "ref_cd74316b8cc5c101960bc16b9922cc5a",
    "page": 23,
    "kind": "Non morto Medio",
    "type": "Non morto",
    "size": "Medio",
    "align": "caotico malvagio",
    "ac": "12",
    "hp": "58 (13d8)",
    "speed": "0 m, volare 12 m (fluttuare)",
    "gs": "4",
    "abilities": {
      "for": "1",
      "des": "14",
      "cos": "10",
      "int": "12",
      "sag": "11",
      "car": "17"
    },
    "excerpt_sha": "8ddc1cd3d1afd3df447102fbaf622b9b0e4a247aa023525c854040102ddcf24c"
  },
  "Basilisco": {
    "name": "Basilisco",
    "id": "ref_f6c339e03f90d86ba242e86f41cbe958",
    "page": 24,
    "kind": "Mostruosità Media",
    "type": "Mostruosità",
    "size": "Media",
    "align": "senza allineamento",
    "ac": "15 (armatura naturale)",
    "hp": "52 (8d8 + 16)",
    "speed": "6 m",
    "gs": "3",
    "abilities": {
      "for": "16",
      "des": "8",
      "cos": "15",
      "int": "2",
      "sag": "8",
      "car": "7"
    },
    "excerpt_sha": "7ac049dafa6e4bd14b868e2b1f2c2a4e31edd44217a7fbb92a09fc167f70f32c"
  }
}


def source_excerpt(name: str, spec: dict[str, Any]) -> str:
    return (
        f"{name}. {spec['kind']}, {spec['align']}. "
        f"Classe Armatura {spec['ac']}. Punti Ferita {spec['hp']}. "
        f"Velocità {spec['speed']}. Sfida {spec['gs']}."
    )


def audit_source(
    name: str, id_collision: bool, name_collisions: list,
    registered_source: dict[str, Any] | None
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("monster_outside_sealed_window")
    if id_collision or name_collisions:
        raise ValueError("existing_monster_collision")
    expected_source = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": SOURCE_FILE,
        "physical_sha256": SOURCE_SHA,
        "physical_pages": SOURCE_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(registered_source, dict) or any(
        registered_source.get(k) != v for k, v in expected_source.items()
    ):
        raise ValueError("source_registry_mismatch")
    spec = MONSTERS[name]
    if spec["page"] not in (22, 23, 24):
        raise ValueError("page_outside_sealed_window")
    token = f"{SOURCE_ID}|{SOURCE_FILE}|{spec['page']}|{name.casefold()}"
    expected_id = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if spec["id"] != expected_id:
        raise ValueError("deterministic_id_drift")
    excerpt = source_excerpt(name, spec)
    checksum = hashlib.sha256(excerpt.encode()).hexdigest()
    if checksum != spec["excerpt_sha"]:
        raise ValueError("source_statblock_drift")
    attrs = {
        "classe_armatura": spec["ac"],
        "punti_ferita": spec["hp"],
        "velocita": spec["speed"],
        "grado_sfida": spec["gs"],
        "caratteristiche": spec["abilities"],
        "tipo_creatura": spec["type"],
        "taglia": spec["size"],
        "allineamento": spec["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_or_identity_gate")
    match = DICE.fullmatch(spec["hp"])
    if not match:
        raise ValueError("invalid_hit_dice")
    avg, count, faces, bonus = match.groups()
    if (int(count) * (int(faces) + 1)) // 2 + int(bonus or 0) != int(avg):
        raise ValueError("hit_dice_average_mismatch")
    if (
        set(spec["abilities"]) != {"for", "des", "cos", "int", "sag", "car"}
        or any(not 1 <= int(s) <= 30 for s in spec["abilities"].values())
    ):
        raise ValueError("abilities_incomplete_or_out_of_bounds")
    return {
        "id": expected_id, "name": name,
        "page": spec["page"], "source_excerpt": excerpt,
        "source_text_checksum": checksum,
        "attributes": deepcopy(attrs),
        "status": "eligible_short_statblock_after_live_preflight",
        "writes": 0,
    }
