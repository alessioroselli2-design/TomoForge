"""Independent visual source audit of four Italian MM ooze statblocks pp213-215.

Page 212 is general lore, not a monster. No source scans/full ability text or DB writes.
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
    "Ameba Paglierina": {
        "page": 213, "size": "Grande", "ac": "8", "hp": "45 (6d10 + 12)",
        "speed": "3 m, scalare 3 m", "gs": "2",
        "scores": [15, 6, 14, 2, 6, 1],
        "traits": ["Amorfo", "Movimenti del Ragno"], "actions": ["Pseudopode"],
        "reactions": ["Scindersi"],
    },
    "Cubo Gelatinoso": {
        "page": 214, "size": "Grande", "ac": "6", "hp": "84 (8d10 + 40)",
        "speed": "4,5 m", "gs": "2", "scores": [14, 3, 20, 1, 6, 1],
        "traits": ["Cubo di Melma", "Trasparente"],
        "actions": ["Pseudopode", "Avviluppare"], "reactions": [],
    },
    "Melma Grigia": {
        "page": 215, "size": "Media", "ac": "8", "hp": "22 (3d8 + 9)",
        "speed": "3 m, scalare 3 m", "gs": "1/2",
        "scores": [12, 6, 16, 1, 6, 2],
        "traits": ["Amorfo", "Corrodere il Metallo", "Falso Aspetto"],
        "actions": ["Pseudopode"], "reactions": [],
    },
    "Protoplasma Nero": {
        "page": 215, "size": "Grande", "ac": "7", "hp": "85 (10d10 + 30)",
        "speed": "6 m, scalare 6 m", "gs": "4",
        "scores": [16, 5, 16, 1, 6, 1],
        "traits": ["Amorfo", "Forma Corrosiva", "Movimenti del Ragno"],
        "actions": ["Pseudopode"], "reactions": ["Scindersi"],
    },
}
def _sealed_fields(d: dict[str, Any]) -> tuple[Any, ...]:
    return (
        d["page"], d["size"], d["ac"], d["hp"], d["speed"], d["gs"],
        tuple(d["scores"]), tuple(d["traits"]),
        tuple(d["actions"]), tuple(d["reactions"]),
    )

SEALED = {name: _sealed_fields(d) for name, d in _SOURCE.items()}
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
    if _sealed_fields(d) != SEALED[name] or d["page"] not in (213, 214, 215):
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
        "tipo_creatura": "Melma", "taglia": d["size"], "sottotipo_creatura": "",
        "allineamento": "senza allineamento",
        "azioni_nomi_da_completare": list(d["actions"]),
        "reazioni_nomi_da_completare": list(d["reactions"]),
        "azioni_leggendarie_nomi_da_completare": [],
        "tratti_nomi_da_completare": list(d["traits"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt = (
        f"{name}. Melma {d['size']}, senza allineamento. "
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
