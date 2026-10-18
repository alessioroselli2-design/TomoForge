"""Original-source proof: four Italian MM green dragon statblocks p100–101.

The user's licensed 353-page Italian scan is checked by filename and SHA256
against the active Supabase authority. Original page images were inspected:
p100 Ancient and p101 Adult, Young, Wyrmling. This is READ ONLY. Never use
as a bypass for a blocked database write. Actions/traits not yet complete.
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
HIT_DICE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+) [+] ([0-9]+)[)]$")

MONSTERS: dict[str, dict[str, Any]] = {
    "Drago Verde Antico": {
        "page": 100,
        "kind": "Drago Mastodontico",
        "type": "Drago",
        "size": "Mastodontico",
        "align": "legale malvagio",
        "ac": "21 (armatura naturale)",
        "hp": "385 (22d20 + 154)",
        "speed": "12 m, nuotare 12 m, volare 24 m",
        "gs": "22",
        "abilities": {
            "for": "27",
            "des": "12",
            "cos": "25",
            "int": "20",
            "sag": "17",
            "car": "19"
        },
        "id": "ref_cf61868fc2317a7512e9b5c5344bace2",
        "digest": "771330ec1d4c23c364ec6d4c0c4befe5d0fb8a9cca2a846985b5d86fb90ae462"
    },
    "Drago Verde Adulto": {
        "page": 101,
        "kind": "Drago Enorme",
        "type": "Drago",
        "size": "Enorme",
        "align": "legale malvagio",
        "ac": "19 (armatura naturale)",
        "hp": "207 (18d12 + 90)",
        "speed": "12 m, nuotare 12 m, volare 24 m",
        "gs": "15",
        "abilities": {
            "for": "23",
            "des": "12",
            "cos": "21",
            "int": "18",
            "sag": "15",
            "car": "17"
        },
        "id": "ref_1f5804259803eba9f1fac7370793be08",
        "digest": "797d86d4cf3d827a4a299b48f05610a35efbdf914cebe74dc403b3c27c3ce91e"
    },
    "Drago Verde Giovane": {
        "page": 101,
        "kind": "Drago Grande",
        "type": "Drago",
        "size": "Grande",
        "align": "legale malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "136 (16d10 + 48)",
        "speed": "12 m, nuotare 12 m, volare 24 m",
        "gs": "8",
        "abilities": {
            "for": "19",
            "des": "12",
            "cos": "17",
            "int": "16",
            "sag": "13",
            "car": "15"
        },
        "id": "ref_a9d004e75ab53b0069f5d379e06611f4",
        "digest": "e24bc5271d33f9290970b7beccf6af9c15d6efd7477c5f0d6375f918cf5ba372"
    },
    "Drago Verde Cucciolo": {
        "page": 101,
        "kind": "Drago Medio",
        "type": "Drago",
        "size": "Medio",
        "align": "legale malvagio",
        "ac": "17 (armatura naturale)",
        "hp": "38 (7d8 + 7)",
        "speed": "9 m, nuotare 9 m, volare 18 m",
        "gs": "2",
        "abilities": {
            "for": "15",
            "des": "12",
            "cos": "13",
            "int": "14",
            "sag": "11",
            "car": "13"
        },
        "id": "ref_878f87d4f76cc6f712eab6dbad325179",
        "digest": "6a280251eaf0c8e87579c565b326206473f8b45503b002a598aeda25376e235e"
    }
}


def source_excerpt(name: str, data: dict[str, Any]) -> str:
    return (
        f"{name}. {data['kind']}, {data['align']}. "
        f"Classe Armatura {data['ac']}. Punti Ferita {data['hp']}. "
        f"Velocità {data['speed']}. Sfida {data['gs']}."
    )


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    existing_id: bool = False,
    monster_name_matches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unrecognized_original_green_dragon")
    if existing_id or monster_name_matches:
        raise ValueError("monster_duplicate_detected")
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
        catalog.get(k) != v for k, v in expected_catalog.items()
    ):
        raise ValueError("registered_manual_source_mismatch")

    d = MONSTERS[name]
    if d["page"] not in (100, 101):
        raise ValueError("physical_source_page_invalid")
    if d["kind"] != f"{d['type']} {d['size']}":
        raise ValueError("type_or_size_invalid")

    key = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    expected_id = "ref_" + hashlib.sha256(key.encode()).hexdigest()[:32]
    if d["id"] != expected_id:
        raise ValueError("deterministic_source_identity_changed")
    text = source_excerpt(name, d)
    checksum = hashlib.sha256(text.encode()).hexdigest()
    if checksum != d["digest"]:
        raise ValueError("source_core_fields_changed")

    attrs = {
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
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate_failed")
    match = HIT_DICE.fullmatch(d["hp"])
    if match is None:
        raise ValueError("hit_dice_parse_failed")
    avg, n, faces, bonus = map(int, match.groups())
    if avg != n * (faces + 1) // 2 + bonus:
        raise ValueError("hit_dice_average_invalid")
    if set(d["abilities"]) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not str(score).isdigit() or not 1 <= int(score) <= 30
        for score in d["abilities"].values()
    ):
        raise ValueError("incomplete_ability_scores")
    return {
        "id": expected_id,
        "name": name,
        "physical_page": d["page"],
        "source_excerpt": text,
        "source_text_checksum": checksum,
        "attributes": deepcopy(attrs),
        "status": "eligible_core_source_only",
        "writes": 0,
    }
