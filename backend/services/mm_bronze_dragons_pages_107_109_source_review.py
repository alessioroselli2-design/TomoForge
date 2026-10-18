"""Original-source proof: four Italian MM bronze dragon statblocks p107–109.

The user's licensed 353-page Italian scan is checked by filename and SHA256
against the active Supabase authority. Original page images were inspected:
p107 Ancient, p108 Adult and Young, p109 Wyrmling. This is READ ONLY. Never use
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
    "Drago Di Bronzo Antico": {
        "page": 107,
        "kind": "Drago Mastodontico",
        "type": "Drago",
        "size": "Mastodontico",
        "align": "legale buono",
        "ac": "22 (armatura naturale)",
        "hp": "444 (24d20 + 192)",
        "speed": "12 m, nuotare 12 m, volare 24 m",
        "gs": "22",
        "abilities": {
            "for": "29",
            "des": "10",
            "cos": "27",
            "int": "18",
            "sag": "17",
            "car": "21"
        },
        "id": "ref_ddef4449f0c0f56f021272bac393917b",
        "digest": "b00c0f2bd52eea64569b499171fc7ca7e433648ba118e3d5faecc331a975c823"
    },
    "Drago Di Bronzo Adulto": {
        "page": 108,
        "kind": "Drago Enorme",
        "type": "Drago",
        "size": "Enorme",
        "align": "legale buono",
        "ac": "19 (armatura naturale)",
        "hp": "212 (17d12 + 102)",
        "speed": "12 m, nuotare 12 m, volare 24 m",
        "gs": "15",
        "abilities": {
            "for": "25",
            "des": "10",
            "cos": "23",
            "int": "16",
            "sag": "15",
            "car": "19"
        },
        "id": "ref_4008110c5d22103f25634876aa591755",
        "digest": "e3c85d6aa61572bd3b9bce22d23452fcdc076f8cfbca9ff6e47ab28f407df6a4"
    },
    "Drago Di Bronzo Giovane": {
        "page": 108,
        "kind": "Drago Grande",
        "type": "Drago",
        "size": "Grande",
        "align": "legale buono",
        "ac": "18 (armatura naturale)",
        "hp": "142 (15d10 + 60)",
        "speed": "12 m, nuotare 12 m, volare 24 m",
        "gs": "8",
        "abilities": {
            "for": "21",
            "des": "10",
            "cos": "19",
            "int": "14",
            "sag": "13",
            "car": "17"
        },
        "id": "ref_526377fe1644b9c52d575c5a85f403d1",
        "digest": "00880d317fd11b74b12ae7182adc30f1155e52d50dc19fcc3a7a8159f3f4aaa4"
    },
    "Drago Di Bronzo Cucciolo": {
        "page": 109,
        "kind": "Drago Medio",
        "type": "Drago",
        "size": "Medio",
        "align": "legale buono",
        "ac": "17 (armatura naturale)",
        "hp": "32 (5d8 + 10)",
        "speed": "9 m, nuotare 9 m, volare 18 m",
        "gs": "2",
        "abilities": {
            "for": "17",
            "des": "10",
            "cos": "15",
            "int": "12",
            "sag": "11",
            "car": "15"
        },
        "id": "ref_73fe386c78a2238ac7253921eccbfecd",
        "digest": "d761a9942a55830969cfd01a897ca7fe4dc38f7fae0ea8b588f0f11ffb3f1135"
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
    if d["page"] not in (107, 108, 109):
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
