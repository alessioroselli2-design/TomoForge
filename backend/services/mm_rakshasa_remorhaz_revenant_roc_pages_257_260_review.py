"""Independent Italian MM source-check: five statblocks on physical pp257-260.

Checked the 353-page user-owned scanned original by page and fixed registered
SHA-256. Page 258 includes separate young/adult Remorhaz. No licensed full
actions, spells or PDF images committed. No database writes.
"""
from __future__ import annotations

import hashlib
import json
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Rakshasa":{"page":257,"type":"Immondo","size":"Medio","subtype":"","align":"legale malvagio","ac":"16 (armatura naturale)","hp":"110 (13d8 + 52)","speed":"12 m","gs":"13","scores":[14,17,18,13,16,20],"traits":["Immunità alla Magia Limitata","Incantesimi Innati"],"actions":["Multiattacco","Artiglio"]},"Remorhaz Giovane":{"page":258,"type":"Mostruosità","size":"Grande","subtype":"","align":"senza allineamento","ac":"14 (armatura naturale)","hp":"93 (11d10 + 33)","speed":"9 m, scavare 6 m","gs":"5","scores":[18,13,17,3,10,4],"traits":["Corpo Surriscaldato"],"actions":["Morso"]},"Remorhaz":{"page":258,"type":"Mostruosità","size":"Enorme","subtype":"","align":"senza allineamento","ac":"17 (armatura naturale)","hp":"195 (17d12 + 85)","speed":"9 m, scavare 6 m","gs":"11","scores":[24,13,21,4,10,5],"traits":["Corpo Surriscaldato"],"actions":["Morso","Inghiottire"]},"Revenant":{"page":259,"type":"Non morto","size":"Medio","subtype":"","align":"neutrale","ac":"13 (armatura di cuoio)","hp":"136 (16d8 + 64)","speed":"9 m","gs":"5","scores":[18,14,18,13,16,18],"traits":["Rigenerazione","Ringiovanimento","Immunità allo Scacciare","Inseguitore Vendicativo"],"actions":["Multiattacco","Pugno","Sguardo Vendicativo"]},"Roc":{"page":260,"type":"Mostruosità","size":"Mastodontica","subtype":"","align":"senza allineamento","ac":"15 (armatura naturale)","hp":"248 (16d20 + 80)","speed":"6 m, volare 36 m","gs":"11","scores":[28,10,20,3,10,9],"traits":["Vista Acuta"],"actions":["Multiattacco","Becco","Speroni"]}}''')
SEALED = {n: (
    d["page"], d["type"], d["size"], d["subtype"], d["align"],
    d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
    tuple(d["traits"]), tuple(d["actions"]),
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
    fields = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["traits"]), tuple(d["actions"]),
    )
    if fields != SEALED[name] or d["page"] not in (257, 258, 259, 260):
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
        "sottotipo_creatura": d["subtype"], "allineamento": d["align"],
        "tratti_nomi_da_completare": list(d["traits"]),
        "azioni_nomi_da_completare": list(d["actions"]),
        "azioni_leggendarie_nomi_da_completare": [],
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
        "attributes": deepcopy(attrs), "source_excerpt": excerpt,
        "source_text_checksum": hashlib.sha256(excerpt.encode()).hexdigest(),
        "status": "source_checked_essential_statistics_only", "writes": 0,
    }
