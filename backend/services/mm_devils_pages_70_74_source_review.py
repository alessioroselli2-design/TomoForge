"""Five original Italian Monster Manual devils p70–74, read-only source gates.

Owner's licensed 353-page scan source fingerprint verified. Physical p66–69
are devil lore and hierarchy tables only; statblock boxes begin p70.
No PDF/page material copied into repository; zero database writes.
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
HP = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+) [+] ([0-9]+)[)]$")
MONSTERS: dict[str, dict[str, Any]] = {
    "Diavolo Barbuto": {
        "page": 70,
        "kind": "Immondo Medio (diavolo)",
        "type": "Immondo",
        "size": "Medio",
        "align": "legale malvagio",
        "ac": "13 (armatura naturale)",
        "hp": "52 (8d8 + 16)",
        "speed": "9 m",
        "gs": "3",
        "abilities": {
            "for": "16",
            "des": "15",
            "cos": "15",
            "int": "9",
            "sag": "11",
            "car": "11"
        },
        "id": "ref_4b6cead38d014d95ad5dea70bbbb54fb",
        "digest": "fef0a7f3abd4bf50a0381e048b4b6ce4c16b3ba6e1650e9b988bd3008bc6b1e2"
    },
    "Diavolo Cornuto": {
        "page": 71,
        "kind": "Immondo Grande (diavolo)",
        "type": "Immondo",
        "size": "Grande",
        "align": "legale malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "178 (17d10 + 85)",
        "speed": "6 m, volare 18 m",
        "gs": "11",
        "abilities": {
            "for": "22",
            "des": "17",
            "cos": "21",
            "int": "12",
            "sag": "16",
            "car": "17"
        },
        "id": "ref_3fd2fbcc93a90004a81aed5620e17704",
        "digest": "a1300a90b850fa7faaa8500af81c600be2838186d0c8f23aa052604c4f1a7d66"
    },
    "Diavolo D'Ossa": {
        "page": 72,
        "kind": "Immondo Grande (diavolo)",
        "type": "Immondo",
        "size": "Grande",
        "align": "legale malvagio",
        "ac": "19 (armatura naturale)",
        "hp": "142 (15d10 + 60)",
        "speed": "12 m, volare 12 m",
        "gs": "9",
        "abilities": {
            "for": "18",
            "des": "16",
            "cos": "18",
            "int": "13",
            "sag": "14",
            "car": "16"
        },
        "id": "ref_817ed8a491a3c480ff60be1572d7acf3",
        "digest": "1c7794a416b8219bc020620c8a62f7af79d0ed6610c969dddb0f9aba84bfb628"
    },
    "Diavolo Del Ghiaccio": {
        "page": 73,
        "kind": "Immondo Grande (diavolo)",
        "type": "Immondo",
        "size": "Grande",
        "align": "legale malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "180 (19d10 + 76)",
        "speed": "12 m",
        "gs": "14",
        "abilities": {
            "for": "21",
            "des": "14",
            "cos": "18",
            "int": "18",
            "sag": "15",
            "car": "18"
        },
        "id": "ref_910d9927cf3bc0113d996e22bf1ba4c4",
        "digest": "18a1463738c3612a745e154c8ba97373b8022c228069b9672e17cd9e10bf6d8e"
    },
    "Diavolo Della Fossa": {
        "page": 74,
        "kind": "Immondo Grande (diavolo)",
        "type": "Immondo",
        "size": "Grande",
        "align": "legale malvagio",
        "ac": "19 (armatura naturale)",
        "hp": "300 (24d10 + 168)",
        "speed": "9 m, volare 18 m",
        "gs": "20",
        "abilities": {
            "for": "26",
            "des": "14",
            "cos": "24",
            "int": "22",
            "sag": "18",
            "car": "24"
        },
        "id": "ref_8891aaa251602cddf04dd88b3bb48942",
        "digest": "9c2fb8dbaac0ece617330d505b30a3acfd0d5c2f73283059611839cb68796c6a"
    }
}


def short(name: str, m: dict[str, Any]) -> str:
    return (
        f"{name}. {m['kind']}, {m['align']}. "
        f"Classe Armatura {m['ac']}. Punti Ferita {m['hp']}. "
        f"Velocità {m['speed']}. Sfida {m['gs']}."
    )


def audit(
    name: str, source: dict[str, Any] | None,
    existing_id: bool = False,
    duplicate_monster_names: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unknown_original_devil_statblock")
    if existing_id or duplicate_monster_names:
        raise ValueError("monster_collision")
    expected = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(source, dict) or any(
        source.get(k) != value for k, value in expected.items()
    ):
        raise ValueError("registered_source_changed")
    m = MONSTERS[name]
    if m["page"] not in (70, 71, 72, 73, 74):
        raise ValueError("source_page_outside_audit")
    token = f"{SOURCE_ID}|{FILENAME}|{m['page']}|{name.casefold()}"
    identity = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if identity != m["id"]:
        raise ValueError("deterministic_identity_changed")
    excerpt = short(name, m)
    digest = hashlib.sha256(excerpt.encode()).hexdigest()
    if digest != m["digest"]:
        raise ValueError("sealed_original_stats_changed")
    attrs = {
        "classe_armatura": m["ac"], "punti_ferita": m["hp"],
        "velocita": m["speed"], "grado_sfida": m["gs"],
        "caratteristiche": m["abilities"], "tipo_creatura": m["type"],
        "taglia": m["size"], "allineamento": m["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate")
    match = HP.fullmatch(m["hp"])
    if match is None:
        raise ValueError("original_hp_unparseable")
    mean, count, faces, bonus = map(int, match.groups())
    if mean != count * (faces + 1) // 2 + bonus:
        raise ValueError("hit_dice_inconsistent")
    if set(m["abilities"]) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not value.isdigit() or not 1 <= int(value) <= 30
        for value in m["abilities"].values()
    ):
        raise ValueError("ability_scores_invalid")
    return {
        "id": identity, "name": name, "page": m["page"],
        "source_excerpt": excerpt, "source_text_checksum": digest,
        "attributes": deepcopy(attrs), "writes": 0,
    }
