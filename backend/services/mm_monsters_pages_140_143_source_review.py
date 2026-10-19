"""Core-statblock source audit for four original Italian MM p140–143 monsters.

Original licensed 353-page scanned PDF, physical pages 140-143, was visually
inspected and file SHA256 verified. Each page contains one separately boxed
creature: Fuoco Fatuo, Fustigatore, Galeb Duhr, Gargoyle. Action names are
source markers only; full action effects are not yet transcribed. Read-only.
"""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PDF_PAGES = 353
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_SOURCE: dict[str, dict[str, Any]] = {
    "Fuoco Fatuo": {
        "page": 140,
        "type": "Non morto",
        "size": "Minuscolo",
        "align": "caotico malvagio",
        "ac": "19",
        "hp": "22 (9d4)",
        "speed": "0 m, volare 15 m (fluttuare)",
        "gs": "2",
        "scores": [
            1,
            28,
            10,
            13,
            14,
            11
        ],
        "action_names": [
            "Folgore",
            "Invisibilità"
        ]
    },
    "Fustigatore": {
        "page": 141,
        "type": "Mostruosità",
        "size": "Grande",
        "align": "neutrale malvagio",
        "ac": "20 (armatura naturale)",
        "hp": "93 (11d10 + 33)",
        "speed": "3 m, scalare 3 m",
        "gs": "5",
        "scores": [
            18,
            8,
            17,
            7,
            16,
            6
        ],
        "action_names": [
            "Multiattacco",
            "Morso",
            "Tentacolo",
            "Riavvolgere"
        ]
    },
    "Galeb Duhr": {
        "page": 142,
        "type": "Elementale",
        "size": "Medio",
        "align": "neutrale",
        "ac": "16 (armatura naturale)",
        "hp": "85 (9d8 + 45)",
        "speed": "4,5 m (9 m quando rotola, 18 m rotolando in discesa)",
        "gs": "6",
        "scores": [
            20,
            14,
            20,
            11,
            12,
            11
        ],
        "action_names": [
            "Schianto",
            "Animare Macigni"
        ]
    },
    "Gargoyle": {
        "page": 143,
        "type": "Elementale",
        "size": "Medio",
        "align": "caotico malvagio",
        "ac": "15 (armatura naturale)",
        "hp": "52 (7d8 + 21)",
        "speed": "9 m, volare 18 m",
        "gs": "2",
        "scores": [
            15,
            11,
            16,
            6,
            11,
            7
        ],
        "action_names": [
            "Multiattacco",
            "Morso",
            "Artigli"
        ]
    }
}

SEALED = {
    name: (
        d["page"], d["type"], d["size"], d["align"], d["ac"],
        d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["action_names"]),
    )
    for name, d in _SOURCE.items()
}
MONSTERS: dict[str, dict[str, Any]] = {
    name: deepcopy(d) for name, d in _SOURCE.items()
}


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    existing_id: bool = False,
    same_name_monsters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    expected = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PDF_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(key) != val for key, val in expected.items()
    ):
        raise ValueError("registered_source_mismatch")
    if existing_id or same_name_monsters:
        raise ValueError("duplicate_monster")
    if name not in SEALED:
        raise ValueError("original_statblock_not_found")

    d = MONSTERS[name]
    actual = (
        d["page"], d["type"], d["size"], d["align"], d["ac"],
        d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["action_names"]),
    )
    if actual != SEALED[name]:
        raise ValueError("source_fields_changed")

    hp_match = HP_RE.fullmatch(d["hp"])
    if hp_match is None:
        raise ValueError("hit_dice_unparseable")
    average, n, faces, operator, adjust = hp_match.groups()
    bonus = int(adjust or 0) * (-1 if operator == "-" else 1)
    if int(average) != int(n) * (int(faces) + 1) // 2 + bonus:
        raise ValueError("hit_dice_mean_mismatch")
    if len(d["scores"]) != 6 or any(
        not isinstance(score, int) or not 1 <= score <= 30 for score in d["scores"]
    ):
        raise ValueError("missing_six_scores")

    attrs = {
        "classe_armatura": d["ac"],
        "punti_ferita": d["hp"],
        "velocita": d["speed"],
        "grado_sfida": d["gs"],
        "caratteristiche": dict(zip(
            ("for", "des", "cos", "int", "sag", "car"),
            (str(x) for x in d["scores"]),
        )),
        "tipo_creatura": d["type"],
        "taglia": d["size"],
        "allineamento": d["align"],
        "azioni_nomi_da_completare": list(d["action_names"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate_failed")
    summary = (
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    source_token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    identifier = "ref_" + hashlib.sha256(source_token.encode()).hexdigest()[:32]
    return {
        "id": identifier,
        "name": name,
        "physical_page": d["page"],
        "source_excerpt": summary,
        "source_text_checksum": hashlib.sha256(summary.encode()).hexdigest(),
        "attributes": deepcopy(attrs),
        "status": "source_verified_core_only",
        "writes": 0,
    }
