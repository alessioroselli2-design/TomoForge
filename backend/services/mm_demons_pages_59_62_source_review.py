"""Read-only proof of five independent Italian MM demon statblocks, p59–62.

Owner-licensed 353-page scan source SHA matched the active source catalog;
every statblock read from original page image. Page 60 holds two independently
named boxed creatures. No original PDF pages or extended excerpts committed.
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
PAGES = 353
HP = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")

MONSTERS: dict[str, dict[str, Any]] = {
    "Goristro": {
        "page": 59,
        "kind": "Immondo Enorme (demone)",
        "type": "Immondo",
        "size": "Enorme",
        "align": "caotico malvagio",
        "ac": "19 (armatura naturale)",
        "hp": "310 (23d12 + 161)",
        "speed": "12 m",
        "gs": "17",
        "abilities": {
            "for": "25",
            "des": "11",
            "cos": "25",
            "int": "6",
            "sag": "13",
            "car": "14"
        },
        "id": "ref_64c6e598c44b2d660eee956094611a24",
        "digest": "9be8114932bdd7781c4628c152e6f4fc32c9b12367d9a9053a6bc18a8ebe5708"
    },
    "Hezrou": {
        "page": 60,
        "kind": "Immondo Grande (demone)",
        "type": "Immondo",
        "size": "Grande",
        "align": "caotico malvagio",
        "ac": "16 (armatura naturale)",
        "hp": "136 (13d10 + 65)",
        "speed": "9 m",
        "gs": "8",
        "abilities": {
            "for": "19",
            "des": "17",
            "cos": "20",
            "int": "5",
            "sag": "12",
            "car": "13"
        },
        "id": "ref_f280c48be6c9e9f6e57d645f0f2ad2ee",
        "digest": "465d07620fc97621d023c5a305d5dc2edd123c7d491d79915a421cdbcde8b643"
    },
    "Mane": {
        "page": 60,
        "kind": "Immondo Piccolo (demone)",
        "type": "Immondo",
        "size": "Piccolo",
        "align": "caotico malvagio",
        "ac": "9",
        "hp": "9 (2d6 + 2)",
        "speed": "6 m",
        "gs": "1/8",
        "abilities": {
            "for": "10",
            "des": "9",
            "cos": "13",
            "int": "3",
            "sag": "8",
            "car": "4"
        },
        "id": "ref_33fbe961393fb032adcabeaf2d4e7049",
        "digest": "964e3b9cdb2d71e78cc78eb71b9b29c07e951e2edd881457125b5aa1c1d9f898"
    },
    "Marilith": {
        "page": 61,
        "kind": "Immondo Grande (demone)",
        "type": "Immondo",
        "size": "Grande",
        "align": "caotico malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "189 (18d10 + 90)",
        "speed": "12 m",
        "gs": "16",
        "abilities": {
            "for": "18",
            "des": "20",
            "cos": "20",
            "int": "18",
            "sag": "16",
            "car": "20"
        },
        "id": "ref_7e06ce5f19b90276328448a1de9e3818",
        "digest": "c5a2625013d3a5b7fe4040edfa9f7075db7532fd659145da361d4a1fbd30324a"
    },
    "Nalfeshnee": {
        "page": 62,
        "kind": "Immondo Grande (demone)",
        "type": "Immondo",
        "size": "Grande",
        "align": "caotico malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "184 (16d10 + 96)",
        "speed": "6 m, volare 9 m",
        "gs": "13",
        "abilities": {
            "for": "21",
            "des": "10",
            "cos": "22",
            "int": "19",
            "sag": "12",
            "car": "15"
        },
        "id": "ref_ff7c88cfebf28f9ae2e0966cd922cab2",
        "digest": "f92529e47edfd0fd68727b9aa75160b29720a1cd8e8223c67af57af7ff4aa56c"
    }
}


def short_source(name: str, m: dict[str, Any]) -> str:
    return (
        f"{name}. {m['kind']}, {m['align']}. "
        f"Classe Armatura {m['ac']}. Punti Ferita {m['hp']}. "
        f"Velocità {m['speed']}. Sfida {m['gs']}."
    )


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    duplicate_id: bool = False,
    duplicate_names: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unexpected_original_demon_statblock")
    if duplicate_id or duplicate_names:
        raise ValueError("monster_duplicate")
    exact_source = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGES,
        "source_role": "authority",
        "source_status": "active",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(k) != value for k, value in exact_source.items()
    ):
        raise ValueError("source_authority_changed")
    m = MONSTERS[name]
    if m["page"] not in (59, 60, 61, 62):
        raise ValueError("physical_page_not_valid")
    token = f"{SOURCE_ID}|{FILENAME}|{m['page']}|{name.casefold()}"
    expected_id = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if expected_id != m["id"]:
        raise ValueError("source_identity_changed")
    short = short_source(name, m)
    checksum = hashlib.sha256(short.encode()).hexdigest()
    if checksum != m["digest"]:
        raise ValueError("sealed_statblock_changed")
    attrs = {
        "classe_armatura": m["ac"],
        "punti_ferita": m["hp"],
        "velocita": m["speed"],
        "grado_sfida": m["gs"],
        "caratteristiche": m["abilities"],
        "tipo_creatura": m["type"],
        "taglia": m["size"],
        "allineamento": m["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate_failed")
    hp = HP.fullmatch(m["hp"])
    if hp is None:
        raise ValueError("cannot_parse_hit_dice")
    average, dice, faces, bonus = hp.groups()
    if int(average) != int(dice) * (int(faces) + 1) // 2 + int(bonus or 0):
        raise ValueError("invalid_hit_dice_average")
    if set(m["abilities"]) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not v.isdigit() or not 1 <= int(v) <= 30 for v in m["abilities"].values()
    ):
        raise ValueError("six_characteristics_missing")
    return {
        "id": expected_id, "name": name, "physical_page": m["page"],
        "source_excerpt": short, "source_text_checksum": checksum,
        "attributes": deepcopy(attrs), "writes": 0,
    }
