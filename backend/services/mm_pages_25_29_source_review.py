"""Bounded original-source audit for Behir, Beholder and Tiranno Della Morte.

Italian user-provided licensed MM: physical pages 25, 28, 29. Pages 26–27
contain beholder lore/lair material, not additional statblocks. Gate checks
do not perform writes; narrative-only Eberron Beholder (other/verified)
is not an existing *monster* statblock and must not be overwritten.
"""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import (
    monster_identity_sanity_flags, monster_semantic_numeric_flags,
)

FILE = "847921086-Manuale-Dei-Mostri-5e.pdf"
SOURCE_ID = "mm_2014_it"
SOURCE_SHA = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
SOURCE_PAGES = 353
SPECIES = {
  "Behir": {
    "id": "ref_182e3ec8c331f6112948df6474cb2120",
    "page": 25,
    "kind": "Mostruosità Enorme",
    "type": "Mostruosità",
    "size": "Enorme",
    "align": "neutrale malvagio",
    "ac": "17 (armatura naturale)",
    "hp": "168 (16d12 + 64)",
    "speed": "15 m, scalare 12 m",
    "gs": "11",
    "abilities": {
      "for": "23",
      "des": "16",
      "cos": "18",
      "int": "7",
      "sag": "14",
      "car": "12"
    },
    "sha": "dec4cfa1a52591ff2badfef62dceec0c6a5d18178cfcef5148956bee68c289d2"
  },
  "Beholder": {
    "id": "ref_2da7c9c7d89fc95b6b559c803f79ec0a",
    "page": 28,
    "kind": "Aberrazione Grande",
    "type": "Aberrazione",
    "size": "Grande",
    "align": "legale malvagio",
    "ac": "18 (armatura naturale)",
    "hp": "180 (19d10 + 76)",
    "speed": "0 m, volare 6 m (fluttuare)",
    "gs": "13",
    "abilities": {
      "for": "10",
      "des": "14",
      "cos": "18",
      "int": "17",
      "sag": "15",
      "car": "17"
    },
    "sha": "84f6b503fedf9978b711bc7d9982c1316fd792f1c6600d4d797e07c229e5f476"
  },
  "Tiranno Della Morte": {
    "id": "ref_345aba979a9262832adf9971e348a35d",
    "page": 29,
    "kind": "Non morto Grande",
    "type": "Non morto",
    "size": "Grande",
    "align": "legale malvagio",
    "ac": "19 (armatura naturale)",
    "hp": "187 (25d10 + 50)",
    "speed": "0 m, volare 6 m (fluttuare)",
    "gs": "14",
    "abilities": {
      "for": "10",
      "des": "14",
      "cos": "14",
      "int": "19",
      "sag": "15",
      "car": "19"
    },
    "sha": "06d8356daa514b8807f9d44d432f136767e4a7d3bd898df74b89b6fb50c27d4d"
  }
}
_DICE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")


def original_excerpt(name: str, d: dict[str, Any]) -> str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )


def audit_mm_block(
    name: str,
    source: dict[str, Any] | None,
    monster_id_collision: bool,
    monster_name_collisions: list[dict[str, Any]],
) -> dict[str, Any]:
    if name not in SPECIES:
        raise ValueError("unexpected_statblock")
    if monster_id_collision or monster_name_collisions:
        raise ValueError("independent_monster_already_present")
    registered = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILE,
        "physical_sha256": SOURCE_SHA, "physical_pages": SOURCE_PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(source, dict) or any(
        source.get(k) != v for k, v in registered.items()
    ):
        raise ValueError("catalog_source_mismatch")
    d = SPECIES[name]
    if d["page"] not in (25, 28, 29):
        raise ValueError("statblock_page_outside_window")
    token = f"{SOURCE_ID}|{FILE}|{d['page']}|{name.casefold()}"
    rec_id = "ref_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
    if d["id"] != rec_id:
        raise ValueError("deterministic_source_id_changed")
    excerpt = original_excerpt(name, d)
    check = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    if check != d["sha"]:
        raise ValueError("sealed_visual_statblock_mismatch")
    attrs = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "caratteristiche": d["abilities"], "tipo_creatura": d["type"],
        "taglia": d["size"], "allineamento": d["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_identity_or_numeric_gate")
    hp = _DICE.fullmatch(d["hp"])
    if not hp:
        raise ValueError("hit_dice_unreadable")
    avg, count, faces, modifier = hp.groups()
    if int(avg) != int(count) * (int(faces)+1) // 2 + int(modifier or 0):
        raise ValueError("hit_dice_math_failed")
    if set(d["abilities"]) != {"for","des","cos","int","sag","car"} or any(
        not 1 <= int(v) <= 30 for v in d["abilities"].values()
    ):
        raise ValueError("six_ability_scores_missing")
    return {
        "status": "eligible_source_confirmed_core_statblock",
        "id": rec_id, "name": name, "page": d["page"],
        "source_excerpt": excerpt, "source_text_checksum": check,
        "attributes": deepcopy(attrs), "writes": 0,
    }
