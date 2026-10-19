"""Italian Monster Manual p233–235: four independent source-checked statblocks.

Source: owner's 353-page scanned 2014 Italian MM with exact registered SHA256.
No private page imagery, spell lists or full licensed rules prose is committed.
Ringiovanimento and legendary actions remain labels pending textual enrichment.
"""
from __future__ import annotations
import hashlib
import json
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Signore delle Mummie":{"page":233,"type":"Non morto","size":"Medio","align":"legale malvagio","ac":"17 (armatura naturale)","hp":"97 (13d8 + 39)","speed":"6 m","gs":"15","scores":[18,10,17,11,18,16],"traits":["Resistenza alla Magia","Ringiovanimento","Incantesimi"],"actions":["Multiattacco","Pugno di Putrefazione","Sguardo Funesto"],"legendary":["Attacco","Polvere Accecante","Parola Blasfema","Incanalare Energia Negativa","Turbine di Sabbia"]},"Naga d'Ossa":{"page":234,"type":"Non morto","size":"Grande","align":"legale malvagio","ac":"15 (armatura naturale)","hp":"58 (9d10 + 9)","speed":"9 m","gs":"4","scores":[15,16,12,15,15,16],"traits":["Incantesimi"],"actions":["Morso"],"legendary":[]},"Naga Spirituale":{"page":235,"type":"Mostruosità","size":"Grande","align":"caotico malvagio","ac":"15 (armatura naturale)","hp":"75 (10d10 + 20)","speed":"12 m","gs":"8","scores":[18,17,14,16,15,16],"traits":["Ringiovanimento","Incantesimi"],"actions":["Morso"],"legendary":[]},"Naga Guardiana":{"page":235,"type":"Mostruosità","size":"Grande","align":"legale buono","ac":"18 (armatura naturale)","hp":"127 (15d10 + 45)","speed":"12 m","gs":"10","scores":[19,18,16,16,19,18],"traits":["Ringiovanimento","Incantesimi"],"actions":["Morso","Sputo Velenoso"],"legendary":[]}}''')
SEALED = {n: (
    d["page"], d["type"], d["size"], d["align"], d["ac"], d["hp"],
    d["speed"], d["gs"], tuple(d["scores"]), tuple(d["traits"]),
    tuple(d["actions"]), tuple(d["legendary"]),
) for n, d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")


def audit(
    name: str, catalog: dict[str, Any] | None,
    existing_id: bool = False, same_named_monster: bool = False,
) -> dict[str, Any]:
    required = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILENAME,
        "physical_sha256": SHA256, "physical_pages": PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in required.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("not_an_original_statblock")
    d = MONSTERS[name]
    current = (
        d["page"], d["type"], d["size"], d["align"], d["ac"], d["hp"],
        d["speed"], d["gs"], tuple(d["scores"]), tuple(d["traits"]),
        tuple(d["actions"]), tuple(d["legendary"]),
    )
    if current != SEALED[name] or d["page"] not in (233, 234, 235):
        raise ValueError("source_fields_changed")
    match = HP_RE.fullmatch(d["hp"])
    if match is None:
        raise ValueError("invalid_hit_dice")
    avg, count, sides, sign, modifier = match.groups()
    bonus = int(modifier or 0) * (-1 if sign == "-" else 1)
    if int(avg) != int(count) * (int(sides) + 1) // 2 + bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"]) != 6 or any(type(v) is not int or not 1 <= v <= 30 for v in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attrs = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "caratteristiche": dict(zip(
            ("for", "des", "cos", "int", "sag", "car"),
            (str(s) for s in d["scores"]),
        )),
        "tipo_creatura": d["type"], "taglia": d["size"],
        "sottotipo_creatura": "", "allineamento": d["align"],
        "tratti_nomi_da_completare": list(d["traits"]),
        "azioni_nomi_da_completare": list(d["actions"]),
        "azioni_leggendarie_nomi_da_completare": list(d["legendary"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt = (
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    identity = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {
        "id": "ref_" + hashlib.sha256(identity.encode()).hexdigest()[:32],
        "name": name, "physical_page": d["page"],
        "attributes": deepcopy(attrs),
        "source_excerpt": excerpt,
        "source_text_checksum": hashlib.sha256(excerpt.encode()).hexdigest(),
        "status": "source_checked_essential_statistics_only",
        "writes": 0,
    }
