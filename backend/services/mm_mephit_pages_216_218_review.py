"""Six separate Italian Monster Manual mephit statblocks, physical pp216-218.

Verified visually against the registered owner-provided scan. The generic
'Mephit' lore and conjuring spell sidebar are not additional monster blocks.
Only essential numeric statistics and ability titles, not licensed full text.
"""
from __future__ import annotations
import hashlib
import re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import (
    monster_identity_sanity_flags, monster_semantic_numeric_flags,
)

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES = 353
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_SOURCE: dict[str, dict[str, Any]] = {
    "Mephit del Fango": {
        "page": 216, "ac": "11", "hp": "27 (6d6 + 6)",
        "speed": "6 m, nuotare 6 m, volare 6 m", "gs": "1/4",
        "scores": [8, 12, 12, 9, 11, 7],
        "traits": ["Esplosione Mortale", "Falso Aspetto"],
        "actions": ["Pugni", "Soffio di Fango (Ricarica 6)"],
    },
    "Mephit del Fumo": {
        "page": 216, "ac": "12", "hp": "22 (5d6 + 5)",
        "speed": "9 m, volare 9 m", "gs": "1/4",
        "scores": [6, 14, 12, 10, 10, 11],
        "traits": ["Esplosione Mortale", "Incantesimi Innati (1/Giorno)"],
        "actions": ["Artigli", "Soffio di Cenere (Ricarica 6)"],
    },
    "Mephit del Ghiaccio": {
        "page": 217, "ac": "11", "hp": "21 (6d6)",
        "speed": "9 m, volare 9 m", "gs": "1/2",
        "scores": [7, 13, 10, 9, 11, 12],
        "traits": ["Esplosione Mortale", "Falso Aspetto", "Incantesimi Innati (1/Giorno)"],
        "actions": ["Artigli", "Soffio di Gelo (Ricarica 6)"],
    },
    "Mephit del Magma": {
        "page": 217, "ac": "11", "hp": "22 (5d6 + 5)",
        "speed": "9 m, volare 9 m", "gs": "1/2",
        "scores": [8, 12, 12, 7, 10, 10],
        "traits": ["Esplosione Mortale", "Falso Aspetto", "Incantesimi Innati (1/Giorno)"],
        "actions": ["Artigli", "Soffio di Fuoco (Ricarica 6)"],
    },
    "Mephit del Vapore": {
        "page": 218, "ac": "10", "hp": "21 (6d6)",
        "speed": "9 m, volare 9 m", "gs": "1/4",
        "scores": [5, 11, 10, 11, 10, 12],
        "traits": ["Esplosione Mortale", "Incantesimi Innati (1/Giorno)"],
        "actions": ["Artigli", "Soffio di Vapore (Ricarica 6)"],
    },
    "Mephit della Polvere": {
        "page": 218, "ac": "12", "hp": "17 (5d6)",
        "speed": "9 m, volare 9 m", "gs": "1/2",
        "scores": [5, 14, 10, 9, 11, 10],
        "traits": ["Esplosione Mortale", "Incantesimi Innati (1/Giorno)"],
        "actions": ["Artigli", "Soffio Accecante (Ricarica 6)"],
    },
}

def _fields(d: dict[str, Any]) -> tuple[Any, ...]:
    return (d["page"], d["ac"], d["hp"], d["speed"], d["gs"],
            tuple(d["scores"]), tuple(d["traits"]), tuple(d["actions"]))

SEALED = {name: _fields(d) for name, d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)


def audit(
    name: str, catalog: dict[str, Any] | None,
    existing_id: bool = False, same_named_monster: bool = False,
) -> dict[str, Any]:
    expected = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILENAME,
        "physical_sha256": SHA256, "physical_pages": PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in expected.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("not_a_source_statblock")
    d = MONSTERS[name]
    if _fields(d) != SEALED[name] or d["page"] not in (216, 217, 218):
        raise ValueError("original_source_fields_changed")
    match = HP_RE.fullmatch(d["hp"])
    if not match:
        raise ValueError("invalid_hit_dice")
    avg, count, sides, sign, modifier = match.groups()
    bonus = int(modifier or 0) * (-1 if sign == "-" else 1)
    if int(avg) != (int(count) * (int(sides) + 1)) // 2 + bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"]) != 6 or any(type(v) is not int or not 1 <= v <= 30 for v in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attrs = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "caratteristiche": dict(zip(("for", "des", "cos", "int", "sag", "car"),
                                   (str(v) for v in d["scores"]))),
        "tipo_creatura": "Elementale", "taglia": "Piccolo", "sottotipo_creatura": "",
        "allineamento": "neutrale malvagio",
        "azioni_nomi_da_completare": list(d["actions"]),
        "azioni_leggendarie_nomi_da_completare": [],
        "tratti_nomi_da_completare": list(d["traits"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt = (
        f"{name}. Elementale Piccolo, neutrale malvagio. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {
        "id": "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32],
        "name": name, "physical_page": d["page"],
        "source_excerpt": excerpt,
        "source_text_checksum": hashlib.sha256(excerpt.encode()).hexdigest(),
        "attributes": deepcopy(attrs),
        "status": "source_checked_essential_statistics_only", "writes": 0,
    }
