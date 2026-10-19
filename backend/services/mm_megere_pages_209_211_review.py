"""Italian Monster Manual p209-211: three independently source-checked hags.

No scan, licensed full-text passages or database writes are stored here.
Covens are rule variants, NOT three additional monster statblocks.
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
    "Megera Marina": {
        "page": 209, "type": "Folletto", "size": "Medio", "align": "caotico malvagio",
        "ac": "14 (armatura naturale)", "hp": "52 (7d8 + 21)",
        "speed": "9 m, nuotare 12 m", "gs": "2", "coven_gs": "4",
        "scores": [16, 13, 16, 12, 12, 13],
        "traits": ["Anfibio", "Aspetto Orripilante"],
        "actions": ["Artigli", "Sguardo Mortale", "Aspetto Illusorio"],
    },
    "Megera Notturna": {
        "page": 210, "type": "Immondo", "size": "Medio", "align": "neutrale malvagio",
        "ac": "17 (armatura naturale)", "hp": "112 (15d8 + 45)",
        "speed": "9 m", "gs": "5", "coven_gs": "7",
        "scores": [18, 15, 16, 16, 14, 16],
        "traits": ["Incantesimi Innati", "Resistenza alla Magia"],
        "actions": ["Artigli (Solo Forma di Megera)", "Cambiare Forma",
                    "Forma Eterea", "Infestare Incubi (1/Giorno)"],
    },
    "Megera Verde": {
        "page": 211, "type": "Folletto", "size": "Medio", "align": "neutrale malvagio",
        "ac": "17 (armatura naturale)", "hp": "82 (11d8 + 33)",
        "speed": "9 m", "gs": "3", "coven_gs": "5",
        "scores": [18, 12, 16, 13, 14, 14],
        "traits": ["Anfibio", "Incantesimi Innati", "Imitare"],
        "actions": ["Artigli", "Aspetto Illusorio", "Passaggio Invisibile"],
    },
}
SEALED = {name: (
    d["page"], d["type"], d["size"], d["align"], d["ac"], d["hp"],
    d["speed"], d["gs"], d["coven_gs"], tuple(d["scores"]),
    tuple(d["traits"]), tuple(d["actions"]),
) for name, d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)


def audit(
    name: str, catalog: dict[str, Any] | None,
    existing_id: bool = False, same_named_monster: bool = False,
) -> dict[str, Any]:
    """Build immutable-looking defensive audit output; never write records."""
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
    fields = (
        d["page"], d["type"], d["size"], d["align"], d["ac"], d["hp"],
        d["speed"], d["gs"], d["coven_gs"], tuple(d["scores"]),
        tuple(d["traits"]), tuple(d["actions"]),
    )
    if fields != SEALED[name] or d["page"] not in (209, 210, 211):
        raise ValueError("original_source_fields_changed")
    match = HP_RE.fullmatch(d["hp"])
    if not match:
        raise ValueError("invalid_hit_dice")
    average, count, sides, sign, modifier = match.groups()
    bonus = int(modifier or 0) * (-1 if sign == "-" else 1)
    if int(average) != (int(count) * (int(sides) + 1)) // 2 + bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"]) != 6 or any(type(v) is not int or not 1 <= v <= 30 for v in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attrs = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "grado_sfida_in_congrega": d["coven_gs"],
        "caratteristiche": dict(zip(("for", "des", "cos", "int", "sag", "car"),
                                   (str(v) for v in d["scores"]))),
        "tipo_creatura": d["type"], "taglia": d["size"], "sottotipo_creatura": "",
        "allineamento": d["align"],
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
        f"Velocità {d['speed']}. Sfida {d['gs']}; in congrega {d['coven_gs']}."
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
