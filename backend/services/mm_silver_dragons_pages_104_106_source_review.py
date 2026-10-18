"""Original-source proof: four Italian MM silver dragon statblocks p104–106.

The user's licensed 353-page Italian scan is checked by filename and SHA256
against the active Supabase authority. Original page images were inspected:
p104 Ancient, p105 Adult and p106 Young and Wyrmling. This is READ ONLY. Never use
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
    "Drago D’Argento Antico": {
        "page": 104,
        "kind": "Drago Mastodontico",
        "type": "Drago",
        "size": "Mastodontico",
        "align": "legale buono",
        "ac": "22 (armatura naturale)",
        "hp": "487 (25d20 + 225)",
        "speed": "12 m, volare 24 m",
        "gs": "23",
        "abilities": {
            "for": "30",
            "des": "10",
            "cos": "29",
            "int": "18",
            "sag": "15",
            "car": "23"
        },
        "id": "ref_d06ac81034f7c658e2557c219a485804",
        "digest": "3b880be7aca73f922f999251fd1aec0c0e50ed21190a4c3406290a3f89438ea6"
    },
    "Drago D’Argento Adulto": {
        "page": 105,
        "kind": "Drago Enorme",
        "type": "Drago",
        "size": "Enorme",
        "align": "legale buono",
        "ac": "19 (armatura naturale)",
        "hp": "243 (18d12 + 126)",
        "speed": "12 m, volare 24 m",
        "gs": "16",
        "abilities": {
            "for": "27",
            "des": "10",
            "cos": "25",
            "int": "16",
            "sag": "13",
            "car": "21"
        },
        "id": "ref_a57d9564a6a9deeb6207b7c6ca3dc4a1",
        "digest": "01480fa6737aec8eb5c5621275e4cad79bfd6ca255c9f8621704dc71b7ff42cf"
    },
    "Drago D’Argento Giovane": {
        "page": 106,
        "kind": "Drago Grande",
        "type": "Drago",
        "size": "Grande",
        "align": "legale buono",
        "ac": "18 (armatura naturale)",
        "hp": "168 (16d10 + 80)",
        "speed": "12 m, volare 24 m",
        "gs": "9",
        "abilities": {
            "for": "23",
            "des": "10",
            "cos": "21",
            "int": "14",
            "sag": "11",
            "car": "19"
        },
        "id": "ref_ed7526804378f1d9c50d009b38dd44b9",
        "digest": "724237d5b86fc39a34d4db305e86974b06d992a9580ef881073a01a12644936e"
    },
    "Drago D’Argento Cucciolo": {
        "page": 106,
        "kind": "Drago Medio",
        "type": "Drago",
        "size": "Medio",
        "align": "legale buono",
        "ac": "17 (armatura naturale)",
        "hp": "45 (6d8 + 18)",
        "speed": "9 m, volare 18 m",
        "gs": "2",
        "abilities": {
            "for": "19",
            "des": "10",
            "cos": "17",
            "int": "12",
            "sag": "11",
            "car": "15"
        },
        "id": "ref_d7eefbdaf0f6ab66ea6ad5d1e349da32",
        "digest": "b3324963a62dbc480c82d66e6049abf8d8a8223bcfb1848cfa6434b26319bf87"
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
        raise ValueError("unrecognized_original_silver_dragon")
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
    if d["page"] not in (104, 105, 106):
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
