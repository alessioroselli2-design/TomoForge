"""Original-source audit for two MM monsters and exceptional Demilich HP.

Original user-provided licensed Italian MM 353-page scan was inspected
physically at pages 46–48 with registered whole-file SHA256. Demilich p48
literally says PF 80 (20d4); expected d4 average is 50, so its entry must
remain blocked until the printed-source inconsistency is deliberately resolved.
Zero database writes. No original PDF or bulk copyrighted page text committed.
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
_HP = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+) [+] ([0-9]+)[)]$")

MONSTERS: dict[str, dict[str, Any]] = {
    "Cumulo Strisciante": {
        "id": "ref_424a91d8cdd2fc3a630f8def1a35951a",
        "page": 46, "kind": "Vegetale Grande",
        "type": "Vegetale", "size": "Grande",
        "align": "senza allineamento",
        "ac": "15 (armatura naturale)",
        "hp": "136 (16d10 + 48)",
        "speed": "6 m, nuotare 6 m", "gs": "5",
        "abilities": {
            "for": "18", "des": "8", "cos": "16",
            "int": "5", "sag": "10", "car": "5",
        },
        "digest": "401f1500f83e025b27a99797fcf8c0ace745341937f6c88baa49a5da54483913",
    },
    "Cuspide Letale": {
        "id": "ref_94af88d2dd2a03e03b1678e99de7ca8b",
        "page": 47, "kind": "Mostruosità Media",
        "type": "Mostruosità", "size": "Media",
        "align": "senza allineamento",
        "ac": "15 (armatura naturale)",
        "hp": "22 (3d8 + 9)",
        "speed": "1,5 m, scalare 1,5 m", "gs": "1/2",
        "abilities": {
            "for": "10", "des": "13", "cos": "16",
            "int": "1", "sag": "7", "car": "3",
        },
        "digest": "d9f7a36b6e6f39ed734d4db960e8a6f670bbf6bd227eb1c518231e3ad51cc309",
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
    id_collision: bool = False,
    existing_monsters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("not_an_eligible_source_statblock")
    if id_collision or existing_monsters:
        raise ValueError("monster_already_exists")
    required = {
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
        catalog.get(key) != value for key, value in required.items()
    ):
        raise ValueError("source_registry_mismatch")
    record = MONSTERS[name]
    if record["page"] not in (46, 47):
        raise ValueError("page_drift")
    token = f"{SOURCE_ID}|{FILENAME}|{record['page']}|{name.casefold()}"
    expected_id = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if record["id"] != expected_id:
        raise ValueError("original_source_identity_drift")
    short = excerpt(name, record)
    digest = hashlib.sha256(short.encode()).hexdigest()
    if digest != record["digest"]:
        raise ValueError("original_source_statblock_fields_changed")
    attrs = {
        "classe_armatura": record["ac"],
        "punti_ferita": record["hp"],
        "velocita": record["speed"],
        "grado_sfida": record["gs"],
        "caratteristiche": record["abilities"],
        "tipo_creatura": record["type"],
        "taglia": record["size"],
        "allineamento": record["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_monster_numeric_gate")
    hp = _HP.fullmatch(record["hp"])
    if not hp:
        raise ValueError("unsupported_hit_dice")
    average, count, faces, bonus = map(int, hp.groups())
    if average != count * (faces + 1) // 2 + bonus:
        raise ValueError("hit_dice_average_mismatch")
    if set(record["abilities"]) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not 1 <= int(value) <= 30 for value in record["abilities"].values()
    ):
        raise ValueError("six_ability_scores_invalid")
    return {
        "id": expected_id,
        "name": name,
        "source_page": record["page"],
        "source_excerpt": short,
        "source_text_checksum": digest,
        "attributes": deepcopy(attrs),
        "status": "eligible_source_confirmed_core_statblock",
        "writes": 0,
    }


def demilich_original_hp_discrepancy() -> dict[str, Any]:
    """Return documented p48 inconsistency without certifying a monster."""
    source_average = 80
    dice_count, die = 20, 4
    actual_average = dice_count * (die + 1) // 2
    if actual_average == source_average:
        raise ValueError("demilich_source_discrepancy_no_longer_present")
    return {
        "name": "Demilich",
        "physical_page": 48,
        "source_hit_points": "80 (20d4)",
        "calculated_average": actual_average,
        "status": "blocked_original_printed_hp_math",
        "review_status_not_forced": True,
        "writes": 0,
    }
