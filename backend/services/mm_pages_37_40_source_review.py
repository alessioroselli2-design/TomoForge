"""Read-only source-locked audit of four Italian Monster Manual page 37–40 blocks.

The private original 353-page scan was independently checked by SHA-256,
manually read page by page, and matched against the active licensed source.
Only concise core field summaries belong in GitHub, never full private pages.
No automatic OCR promotion, storage access or database mutation takes place.
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
PHYSICAL_SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGE_COUNT = 353
HP_EXPR = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")

MONSTERS: dict[str, dict[str, Any]] = {
    "Cavaliere Della Morte": {
        "id": "ref_521ba28322b8568f49e4f0734378d1b2",
        "page": 37,
        "kind": "Non morto Medio",
        "type": "Non morto",
        "size": "Medio",
        "align": "caotico malvagio",
        "ac": "20 (armatura completa, scudo)",
        "hp": "180 (19d8 + 95)",
        "speed": "9 m",
        "gs": "17",
        "abilities": {
            "for": "20", "des": "11", "cos": "20",
            "int": "12", "sag": "16", "car": "18",
        },
        "excerpt_sha": "4b7bdb20e929f69034068e0394dddabe7688c229c18f7aa5f8093190bda042a1",
    },
    "Cavallo Degli Incubi": {
        "id": "ref_78cbd1ce560ddd4b5bb824726713892d",
        "page": 38,
        "kind": "Immondo Grande",
        "type": "Immondo",
        "size": "Grande",
        "align": "neutrale malvagio",
        "ac": "13 (armatura naturale)",
        "hp": "68 (8d10 + 24)",
        "speed": "18 m, volare 27 m",
        "gs": "3",
        "abilities": {
            "for": "18", "des": "15", "cos": "16",
            "int": "10", "sag": "13", "car": "15",
        },
        "excerpt_sha": "1f2418b305c6ab16752d9af9734f43190a1a7edbaed15419dbc6b14cdd721d95",
    },
    "Centauro": {
        "id": "ref_81732b7b2d550256674992f7295b0b53",
        "page": 39,
        "kind": "Mostruosità Grande",
        "type": "Mostruosità",
        "size": "Grande",
        "align": "neutrale buono",
        "ac": "12",
        "hp": "45 (6d10 + 12)",
        "speed": "15 m",
        "gs": "2",
        "abilities": {
            "for": "18", "des": "14", "cos": "14",
            "int": "9", "sag": "13", "car": "11",
        },
        "excerpt_sha": "3326c7def0770a21120960454e1ce5d4c86d471f8438fe845a32007641429f82",
    },
    "Chimera": {
        "id": "ref_0629e3b394aced0ebb7999781ec8c979",
        "page": 40,
        "kind": "Mostruosità Grande",
        "type": "Mostruosità",
        "size": "Grande",
        "align": "caotico malvagio",
        "ac": "14 (armatura naturale)",
        "hp": "114 (12d10 + 48)",
        "speed": "9 m, volare 18 m",
        "gs": "6",
        "abilities": {
            "for": "19", "des": "11", "cos": "19",
            "int": "3", "sag": "14", "car": "10",
        },
        "excerpt_sha": "dc65d994c1285032c11a872f9671fd4b8e2cec5e0989daf26313887c2389a9d8",
    },
}


def source_excerpt(name: str, d: dict[str, Any]) -> str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )


def audit_mm_page_37_40(
    name: str,
    catalog: dict[str, Any] | None,
    monster_id_collision: bool = False,
    monster_name_collisions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unknown_statblock")
    if monster_id_collision or monster_name_collisions:
        raise ValueError("already_present_as_monster")
    expected_catalog = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": PHYSICAL_SHA256,
        "physical_pages": PAGE_COUNT,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(key) != expected for key, expected in expected_catalog.items()
    ):
        raise ValueError("original_source_not_verified")

    d = MONSTERS[name]
    if d["page"] not in (37, 38, 39, 40):
        raise ValueError("source_page_outside_batch")
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    identifier = "ref_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
    if d["id"] != identifier:
        raise ValueError("deterministic_reference_id_drift")
    brief = source_excerpt(name, d)
    digest = hashlib.sha256(brief.encode("utf-8")).hexdigest()
    if digest != d["excerpt_sha"]:
        raise ValueError("sealed_source_metrics_changed")
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
        raise ValueError("structural_or_numeric_gate_failed")
    hp = HP_EXPR.fullmatch(d["hp"])
    if not hp:
        raise ValueError("invalid_hit_dice_expression")
    avg, dice, faces, modifier = hp.groups()
    if int(avg) != int(dice) * (int(faces) + 1) // 2 + int(modifier or 0):
        raise ValueError("hit_dice_math_mismatch")
    if set(d["abilities"]) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not value.isdigit() or not 1 <= int(value) <= 30
        for value in d["abilities"].values()
    ):
        raise ValueError("ability_scores_incomplete")

    return {
        "status": "eligible_source_checked_core_statblock",
        "id": identifier,
        "name": name,
        "physical_page": d["page"],
        "source_excerpt": brief,
        "source_text_checksum": digest,
        "attributes": deepcopy(attrs),
        "writes": 0,
    }
