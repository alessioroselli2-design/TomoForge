"""Original-source audit for four distinct Italian Monster Manual genie statblocks.

Physical source pages 146 (Dao), 147 (Djinni), 148 (Efreeti), 149 (Marid)
of user's licensed 353-page Italian manual visually inspected. Page 145 is
lore only and is NOT a statblock. Condensed core values and action names,
not full transcription of innate spells and action mechanics. Read-only.
"""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SOURCE_SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PDF_PAGES = 353
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+) [+] ([0-9]+)[)]$")
_ORIGINAL = {
    "Dao": {
        "page": 146,
        "ac": "18 (armatura naturale)",
        "hp": "187 (15d10 + 105)",
        "speed": "9 m, scavare 9 m, volare 9 m",
        "gs": "11",
        "align": "neutrale malvagio",
        "scores": [
            23,
            12,
            24,
            12,
            13,
            14
        ],
        "actions": [
            "Multiattacco",
            "Pugno",
            "Maglio"
        ]
    },
    "Djinni": {
        "page": 147,
        "ac": "17 (armatura naturale)",
        "hp": "161 (14d10 + 84)",
        "speed": "9 m, volare 27 m",
        "gs": "11",
        "align": "caotico buono",
        "scores": [
            21,
            15,
            22,
            15,
            16,
            20
        ],
        "actions": [
            "Multiattacco",
            "Scimitarra",
            "Creare Vortice"
        ]
    },
    "Efreeti": {
        "page": 148,
        "ac": "17 (armatura naturale)",
        "hp": "200 (16d10 + 112)",
        "speed": "12 m, volare 18 m",
        "gs": "11",
        "align": "legale malvagio",
        "scores": [
            22,
            12,
            24,
            16,
            15,
            16
        ],
        "actions": [
            "Multiattacco",
            "Scimitarra",
            "Scagliare Fiamma"
        ]
    },
    "Marid": {
        "page": 149,
        "ac": "17 (armatura naturale)",
        "hp": "229 (17d10 + 136)",
        "speed": "9 m, volare 18 m, nuotare 27 m",
        "gs": "11",
        "align": "caotico neutrale",
        "scores": [
            22,
            12,
            26,
            18,
            17,
            18
        ],
        "actions": [
            "Multiattacco",
            "Tridente",
            "Getto d'Acqua"
        ]
    }
}
FIELDS = {
    n: (x["page"], x["ac"], x["hp"], x["speed"], x["gs"], x["align"],
        tuple(x["scores"]), tuple(x["actions"]))
    for n, x in _ORIGINAL.items()
}
CREATURES = {name: deepcopy(value) for name, value in _ORIGINAL.items()}


def audit(name: str, catalog: dict[str, Any] | None,
          duplicate_id: bool = False,
          duplicate_names: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SOURCE_SHA256,
        "physical_pages": PDF_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in required.items()):
        raise ValueError("registered_source_mismatch")
    if duplicate_id or duplicate_names:
        raise ValueError("duplicate_monster")
    if name not in FIELDS:
        raise ValueError("no_independent_genie_statblock")
    d = CREATURES[name]
    values = (
        d["page"], d["ac"], d["hp"], d["speed"], d["gs"], d["align"],
        tuple(d["scores"]), tuple(d["actions"]),
    )
    if values != FIELDS[name]:
        raise ValueError("sealed_source_statblock_changed")

    hp = HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_original_hp")
    avg, count, sides, bonus = map(int, hp.groups())
    if avg != count * (sides + 1) // 2 + bonus:
        raise ValueError("hp_arithmetic_failed")
    if len(d["scores"]) != 6 or any(not isinstance(x, int) or not 1 <= x <= 30 for x in d["scores"]):
        raise ValueError("six_ability_scores_missing")
    attrs = {
        "classe_armatura": d["ac"],
        "punti_ferita": d["hp"],
        "velocita": d["speed"],
        "grado_sfida": d["gs"],
        "caratteristiche": dict(zip(
            ("for", "des", "cos", "int", "sag", "car"),
            (str(x) for x in d["scores"]),
        )),
        "tipo_creatura": "Elementale",
        "taglia": "Grande",
        "allineamento": d["align"],
        "azioni_nomi_da_completare": list(d["actions"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_identity_numeric_gate")
    page = d["page"]
    key = f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}"
    short = (
        f"{name}. Elementale Grande, {d['align']}. Classe Armatura {d['ac']}. "
        f"Punti Ferita {d['hp']}. Velocità {d['speed']}. Sfida {d['gs']}."
    )
    return {
        "id": "ref_" + hashlib.sha256(key.encode()).hexdigest()[:32],
        "name": name,
        "physical_page": page,
        "source_excerpt": short,
        "source_text_checksum": hashlib.sha256(short.encode()).hexdigest(),
        "attributes": deepcopy(attrs),
        "writes": 0,
        "status": "original_core_checked",
    }
