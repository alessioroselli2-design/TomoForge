"""Two read-only original-source statblock audits from MM pages 44 and 45.

Checked against the owner's 353-page Italian licensed scan with file SHA-256,
visual confirmation of the printed creature block, and mathematical PF checks.
Does not write to Supabase, read R2 or distribute full PDF page content.
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
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PHYSICAL_PAGES = 353
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")

MONSTERS: dict[str, dict[str, Any]] = {
    "Cockatrice": {
        "id": "ref_e1b293b4afc942d2eb22eb7851df434b",
        "page": 44,
        "kind": "Mostruosità Piccola",
        "type": "Mostruosità",
        "size": "Piccola",
        "align": "senza allineamento",
        "ac": "11",
        "hp": "27 (6d6 + 6)",
        "speed": "6 m, volare 12 m",
        "gs": "1/2",
        "abilities": {
            "for": "6", "des": "12", "cos": "12",
            "int": "2", "sag": "13", "car": "5",
        },
        "checksum": "7188378a6a818e3a153f95092e09f6abdc9acceef41487f8ab5849bc6e416388",
    },
    "Couatl": {
        "id": "ref_fd7adba90643a77fce8895073266772e",
        "page": 45,
        "kind": "Celestiale Medio",
        "type": "Celestiale",
        "size": "Medio",
        "align": "legale buono",
        "ac": "19 (armatura naturale)",
        "hp": "97 (13d8 + 39)",
        "speed": "9 m, volare 27 m",
        "gs": "4",
        "abilities": {
            "for": "16", "des": "20", "cos": "17",
            "int": "18", "sag": "20", "car": "18",
        },
        "checksum": "6121f0dc54bef6759b426ca8d36f3350afbb0562fde8578102645865d2258d51",
    },
}


def original_excerpt(name: str, spec: dict[str, Any]) -> str:
    return (
        f"{name}. {spec['kind']}, {spec['align']}. "
        f"Classe Armatura {spec['ac']}. Punti Ferita {spec['hp']}. "
        f"Velocità {spec['speed']}. Sfida {spec['gs']}."
    )


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    id_collision: bool = False,
    monster_name_collisions: list[dict] | None = None,
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unknown_source_creature")
    if id_collision or monster_name_collisions:
        raise ValueError("duplicate_monster")
    expected_catalog = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PHYSICAL_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(field) != value for field, value in expected_catalog.items()
    ):
        raise ValueError("source_authority_mismatch")

    data = MONSTERS[name]
    if data["page"] not in (44, 45):
        raise ValueError("wrong_visual_source_page")
    token = f"{SOURCE_ID}|{FILENAME}|{data['page']}|{name.casefold()}"
    expected_id = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if expected_id != data["id"]:
        raise ValueError("deterministic_source_identity_changed")
    excerpt = original_excerpt(name, data)
    digest = hashlib.sha256(excerpt.encode()).hexdigest()
    if digest != data["checksum"]:
        raise ValueError("original_statblock_fields_modified")
    attributes = {
        "classe_armatura": data["ac"],
        "punti_ferita": data["hp"],
        "velocita": data["speed"],
        "grado_sfida": data["gs"],
        "caratteristiche": data["abilities"],
        "tipo_creatura": data["type"],
        "taglia": data["size"],
        "allineamento": data["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attributes):
        raise ValueError("statblock_numeric_or_identity_gate")
    hp = HP_RE.fullmatch(data["hp"])
    if hp is None:
        raise ValueError("invalid_hp_dice_notation")
    avg, count, faces, bonus = hp.groups()
    if int(avg) != int(count) * (int(faces) + 1) // 2 + int(bonus or 0):
        raise ValueError("mathematically_incorrect_hp")
    if set(data["abilities"]) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not val.isdigit() or not 1 <= int(val) <= 30
        for val in data["abilities"].values()
    ):
        raise ValueError("incomplete_six_ability_scores")
    return {
        "id": expected_id,
        "name": name,
        "physical_page": data["page"],
        "source_excerpt": excerpt,
        "source_text_checksum": digest,
        "attributes": deepcopy(attributes),
        "status": "eligible_original_source_core_statblock",
        "writes": 0,
    }
