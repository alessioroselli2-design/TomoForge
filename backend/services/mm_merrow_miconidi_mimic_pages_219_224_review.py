"""Seven statblocks from original Italian Monster Manual physical pp219-224.

Page 222 has Miconide illustration, not its own statblock. The Quaggoth
Spore Servant is a genuine independently boxed example statblock.
Only core statistics and short feature/action labels; no PDF and no DB writes.
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
    "Merrow": {
        "page": 219, "type": "Mostruosità", "size": "Grande", "subtype": "",
        "align": "caotico malvagio", "ac": "13 (armatura naturale)",
        "hp": "45 (6d10 + 12)", "speed": "3 m, nuotare 12 m", "gs": "2",
        "scores": [18, 10, 15, 8, 10, 9], "traits": ["Anfibio"],
        "actions": ["Multiattacco", "Morso", "Artigli", "Arpione"],
    },
    "Mezzodrago Rosso Veterano": {
        "page": 220, "type": "Umanoide", "size": "Medio", "subtype": "umano",
        "align": "qualsiasi allineamento", "ac": "18 (armatura completa)",
        "hp": "65 (10d8 + 20)", "speed": "9 m", "gs": "5",
        "scores": [16, 13, 14, 10, 11, 10], "traits": [],
        "actions": ["Multiattacco", "Spada Lunga", "Spada Corta",
                    "Balestra Pesante", "Soffio di Fuoco (Ricarica 5-6)"],
    },
    "Miconide Germoglio": {
        "page": 221, "type": "Vegetale", "size": "Piccolo", "subtype": "",
        "align": "legale neutrale", "ac": "10", "hp": "7 (2d6)",
        "speed": "3 m", "gs": "0", "scores": [8, 10, 10, 8, 11, 5],
        "traits": ["Spore Segnalatrici", "Eliofobia"],
        "actions": ["Pugno", "Spore Comunicanti (3/Giorno)"],
    },
    "Quaggoth Servitore delle Spore": {
        "page": 221, "type": "Vegetale", "size": "Medio", "subtype": "",
        "align": "senza allineamento", "ac": "13 (armatura naturale)",
        "hp": "45 (6d8 + 18)", "speed": "6 m, scalare 6 m", "gs": "1",
        "scores": [17, 12, 16, 2, 6, 1], "traits": [],
        "actions": ["Multiattacco", "Artiglio"],
    },
    "Miconide Adulto": {
        "page": 223, "type": "Vegetale", "size": "Medio", "subtype": "",
        "align": "legale neutrale", "ac": "12 (armatura naturale)",
        "hp": "22 (4d8 + 4)", "speed": "6 m", "gs": "1/2",
        "scores": [10, 10, 12, 10, 13, 7],
        "traits": ["Spore Segnalatrici", "Eliofobia"],
        "actions": ["Pugno", "Spore Pacificatrici (3/Giorno)", "Spore Comunicanti"],
    },
    "Miconide Sovrano": {
        "page": 223, "type": "Vegetale", "size": "Grande", "subtype": "",
        "align": "legale neutrale", "ac": "13 (armatura naturale)",
        "hp": "60 (8d10 + 16)", "speed": "9 m", "gs": "2",
        "scores": [12, 10, 14, 13, 15, 10],
        "traits": ["Spore Segnalatrici", "Eliofobia"],
        "actions": ["Multiattacco", "Pugno", "Spore Animanti (3/Giorno)",
                    "Spore Allucinogene", "Spore Pacificatrici", "Spore Comunicanti"],
    },
    "Mimic": {
        "page": 224, "type": "Mostruosità", "size": "Medio", "subtype": "mutaforma",
        "align": "neutrale", "ac": "12 (armatura naturale)",
        "hp": "58 (9d8 + 18)", "speed": "4,5 m", "gs": "2",
        "scores": [17, 12, 15, 5, 13, 8],
        "traits": ["Mutaforma", "Adesivo (Solo Forma di Oggetto)",
                   "Falso Aspetto (Solo Forma di Oggetto)", "Lottatore"],
        "actions": ["Pseudopode", "Morso"],
    },
}

def _fields(d: dict[str, Any]) -> tuple[Any, ...]:
    return (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["traits"]), tuple(d["actions"]),
    )

SEALED = {n: _fields(d) for n, d in _SOURCE.items()}
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
    if _fields(d) != SEALED[name] or d["page"] not in (219, 220, 221, 223, 224):
        raise ValueError("original_source_fields_changed")
    hp = HP_RE.fullmatch(d["hp"])
    if not hp:
        raise ValueError("invalid_hit_dice")
    avg, count, sides, sign, modifier = hp.groups()
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
        "tipo_creatura": d["type"], "taglia": d["size"],
        "sottotipo_creatura": d["subtype"], "allineamento": d["align"],
        "azioni_nomi_da_completare": list(d["actions"]),
        "azioni_leggendarie_nomi_da_completare": [],
        "tratti_nomi_da_completare": list(d["traits"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt = (
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
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
