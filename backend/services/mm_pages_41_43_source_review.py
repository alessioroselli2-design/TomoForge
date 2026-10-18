"""Fail-closed original-source proof for MM page 41–43 monster blocks.

Original user-licensed Italian 353-page MM file SHA-256 and physical page boxes
checked independently. Page 43 has *two* distinct kobold monster statblocks,
not one race/species header. This module is read-only and stores no source PDF.
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
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES = 353
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")

MONSTERS: dict[str, dict[str, Any]] = {
    "Chuul": {
        "id": "ref_153ae6ed4615951279cb9eb50c7422f9",
        "page": 41, "kind": "Aberrazione Grande",
        "type": "Aberrazione", "size": "Grande",
        "align": "caotico malvagio",
        "ac": "16 (armatura naturale)", "hp": "93 (11d10 + 33)",
        "speed": "9 m, nuotare 9 m", "gs": "4",
        "abilities": {
            "for": "19", "des": "10", "cos": "16",
            "int": "5", "sag": "11", "car": "5",
        },
        "digest": "fceb38d4345353941d91a4bdca603de6efd87e0eb252b8d6d501d7feb33c38cd",
    },
    "Ciclope": {
        "id": "ref_b8f3214dac38dc5a42bc54b58c6645a8",
        "page": 42, "kind": "Gigante Enorme",
        "type": "Gigante", "size": "Enorme",
        "align": "caotico neutrale",
        "ac": "14 (armatura naturale)", "hp": "138 (12d12 + 60)",
        "speed": "9 m", "gs": "6",
        "abilities": {
            "for": "22", "des": "11", "cos": "20",
            "int": "8", "sag": "6", "car": "10",
        },
        "digest": "ce8462c205f348cca76206bbe5118ae767bb00a389d3877543599546595e8770",
    },
    "Coboldo Alato": {
        "id": "ref_73bba306c5c3da8c2f2874f1e1e3fe3c",
        "page": 43, "kind": "Umanoide Piccolo (coboldo)",
        "type": "Umanoide", "size": "Piccolo",
        "align": "legale malvagio",
        "ac": "13", "hp": "7 (3d6 - 3)",
        "speed": "9 m, volare 9 m", "gs": "1/4",
        "abilities": {
            "for": "7", "des": "16", "cos": "9",
            "int": "8", "sag": "7", "car": "8",
        },
        "digest": "ba1fc17115f732c229cdfbb434a891c40685cf82874470d2001c86edfac1279b",
    },
    "Coboldo": {
        "id": "ref_8defe4e33fdbedb1d8bf7417884622cb",
        "page": 43, "kind": "Umanoide Piccolo (coboldo)",
        "type": "Umanoide", "size": "Piccolo",
        "align": "legale malvagio",
        "ac": "12", "hp": "5 (2d6 - 2)",
        "speed": "9 m", "gs": "1/8",
        "abilities": {
            "for": "7", "des": "15", "cos": "9",
            "int": "8", "sag": "7", "car": "8",
        },
        "digest": "90921bdef82f212baad4fc10991099a8fa6b00f18b157d4b1716492cbf24933a",
    },
}


def excerpt(name: str, d: dict[str, Any]) -> str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    existing_id: bool = False,
    existing_monster_names: list[dict] | None = None,
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("missing_named_statblock")
    if existing_id or existing_monster_names:
        raise ValueError("monster_duplicate_detected")
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA,
        "physical_pages": PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(field) != expected for field, expected in required.items()
    ):
        raise ValueError("registered_source_mismatch")
    d = MONSTERS[name]
    if d["page"] not in (41, 42, 43):
        raise ValueError("wrong_source_page")
    original_token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    expected_id = "ref_" + hashlib.sha256(original_token.encode()).hexdigest()[:32]
    if expected_id != d["id"]:
        raise ValueError("original_statblock_identity_changed")
    source = excerpt(name, d)
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != d["digest"]:
        raise ValueError("source_fields_unsealed_or_changed")
    attributes = {
        "classe_armatura": d["ac"],
        "punti_ferita": d["hp"],
        "velocita": d["speed"],
        "grado_sfida": d["gs"],
        "caratteristiche": d["abilities"],
        "tipo_creatura": d["type"],
        "taglia": d["size"],
        "allineamento": d["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attributes):
        raise ValueError("monster_semantic_numeric_gate_failed")
    match = HP_RE.fullmatch(d["hp"])
    if match is None:
        raise ValueError("unparseable_original_hit_dice")
    average, count, faces, operator, delta = match.groups()
    modifier = int(delta or 0) * (-1 if operator == "-" else 1)
    if int(average) != int(count) * (int(faces) + 1) // 2 + modifier:
        raise ValueError("hit_dice_arithmetic_failed")
    abilities = d["abilities"]
    if set(abilities) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not value.isdigit() or not 1 <= int(value) <= 30
        for value in abilities.values()
    ):
        raise ValueError("six_ability_scores_missing")
    return {
        "id": expected_id,
        "name": name,
        "physical_page": d["page"],
        "attributes": deepcopy(attributes),
        "source_excerpt": source,
        "source_text_checksum": digest,
        "status": "eligible_original_visual_core_statblock",
        "writes": 0,
    }
