"""MM p63–65 original-source audit: Quasit duplicate, Vrock and Yochlol.

Source: owner's licensed 353-page Italian scan, SHA-256 matched. The Quasit
on original p63 is already a monster/verified in PHB, not a new monster.
Page 66 begins a new devil lore section and is not a demon statblock.
This module performs no database writes.
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
PHB_QUASIT_ID = "ref_867c68436df55ff48716ebe704da4044"
HP = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+) [+] ([0-9]+)[)]$")
MONSTERS: dict[str, dict[str, Any]] = {
    "Vrock": {
        "id": "ref_4f31f61ddb5b3bb90619332bd26495c9",
        "page": 64, "kind": "Immondo Grande (demone)", "type": "Immondo",
        "size": "Grande", "align": "caotico malvagio",
        "ac": "15 (armatura naturale)", "hp": "104 (11d10 + 44)",
        "speed": "12 m, volare 18 m", "gs": "6",
        "abilities": {
            "for": "17", "des": "15", "cos": "18",
            "int": "8", "sag": "13", "car": "8",
        },
        "digest": "d911f60de69ae804866ff64d44285f6c88f79bf036570198ce06548bf2c888d8",
    },
    "Yochlol": {
        "id": "ref_36fa466bd66e0fa9c148a5cdf7602640",
        "page": 65, "kind": "Immondo Medio (demone, mutaforma)", "type": "Immondo",
        "size": "Medio", "align": "caotico malvagio",
        "ac": "15 (armatura naturale)", "hp": "136 (16d8 + 64)",
        "speed": "9 m, scalare 9 m", "gs": "10",
        "abilities": {
            "for": "15", "des": "14", "cos": "18",
            "int": "13", "sag": "15", "car": "15",
        },
        "digest": "3bcb4b8d0e1d0861609cca847cb72b7c86ee17c3ca0ced71e67c952f2040d3ae",
    },
}


def short(name: str, d: dict[str, Any]) -> str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    id_found: bool = False,
    names_found: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if name == "Quasit":
        raise ValueError("already_verified_phb_quasit_do_not_duplicate")
    if name not in MONSTERS:
        raise ValueError("unknown_statblock")
    if id_found or names_found:
        raise ValueError("monster_duplicate")
    expected_source = {
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
        catalog.get(k) != v for k, v in expected_source.items()
    ):
        raise ValueError("registered_source_changed")
    d = MONSTERS[name]
    if d["page"] not in (64, 65):
        raise ValueError("source_page_not_in_batch")
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    candidate_id = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if candidate_id != d["id"]:
        raise ValueError("original_identity_drift")
    excerpt = short(name, d)
    digest = hashlib.sha256(excerpt.encode()).hexdigest()
    if digest != d["digest"]:
        raise ValueError("source_statblock_drift")
    attrs = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "caratteristiche": d["abilities"], "tipo_creatura": d["type"],
        "taglia": d["size"], "allineamento": d["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate_failed")
    hp = HP.fullmatch(d["hp"])
    if not hp:
        raise ValueError("invalid_hp_source_expression")
    mean, count, faces, bonus = map(int, hp.groups())
    if mean != count * (faces + 1) // 2 + bonus:
        raise ValueError("invalid_hp_average")
    if set(d["abilities"]) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not v.isdigit() or not 1 <= int(v) <= 30 for v in d["abilities"].values()
    ):
        raise ValueError("six_scores_invalid")
    return {
        "id": candidate_id, "name": name, "page": d["page"],
        "source_excerpt": excerpt, "source_text_checksum": digest,
        "attributes": deepcopy(attrs), "writes": 0,
    }
