"""Original 2014 Italian Monster Manual p257-264 ten physical statblocks.

Owner-provided licensed PDF visually inspected, source catalog SHA confirmed.
Only short fields/ability titles, no original scans, full rules or DB writes.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Rakshasa":{"page":257,"type":"Immondo","size":"Medio","subtype":"","align":"legale malvagio","ac":"16 (armatura naturale)","hp":"110 (13d8 + 52)","speed":"12 m","gs":"13","scores":[14,17,18,13,16,20],"traits":["Immunità alla Magia Limitata","Incantesimi Innati"],"actions":["Multiattacco","Artiglio"]},"Remorhaz Giovane":{"page":258,"type":"Mostruosità","size":"Grande","subtype":"","align":"senza allineamento","ac":"14 (armatura naturale)","hp":"93 (11d10 + 33)","speed":"9 m, scavare 6 m","gs":"5","scores":[18,13,17,3,10,4],"traits":["Corpo Surriscaldato"],"actions":["Morso"]},"Remorhaz":{"page":258,"type":"Mostruosità","size":"Enorme","subtype":"","align":"senza allineamento","ac":"17 (armatura naturale)","hp":"195 (17d12 + 85)","speed":"9 m, scavare 6 m","gs":"11","scores":[24,13,21,4,10,5],"traits":["Corpo Surriscaldato"],"actions":["Morso","Inghiottire"]},"Revenant":{"page":259,"type":"Non morto","size":"Medio","subtype":"","align":"neutrale","ac":"13 (armatura di cuoio)","hp":"136 (16d8 + 64)","speed":"9 m","gs":"5","scores":[18,14,18,13,16,18],"traits":["Rigenerazione","Ringiovanimento"],"actions":["Multiattacco","Pugno","Sguardo Vendicativo"]},"Roc":{"page":260,"type":"Mostruosità","size":"Mastodontica","subtype":"","align":"senza allineamento","ac":"15 (armatura naturale)","hp":"248 (16d20 + 80)","speed":"6 m, volare 36 m","gs":"11","scores":[28,10,20,3,10,9],"traits":["Vista Acuta"],"actions":["Multiattacco","Becco","Speroni"]},"Rugginofago":{"page":261,"type":"Mostruosità","size":"Media","subtype":"","align":"senza allineamento","ac":"14 (armatura naturale)","hp":"27 (5d8 + 5)","speed":"12 m","gs":"1/2","scores":[13,12,13,2,13,6],"traits":["Fiutare il Ferro","Arrugginire"],"actions":["Morso","Antenne"]},"Sahuagin":{"page":262,"type":"Umanoide","size":"Medio","subtype":"sahuagin","align":"legale malvagio","ac":"12 (armatura naturale)","hp":"22 (4d8 + 4)","speed":"9 m, nuotare 12 m","gs":"1/2","scores":[13,11,12,12,13,9],"traits":["Frenesia di Sangue","Anfibio Limitato","Telepatia con gli Squali"],"actions":["Multiattacco","Morso","Artigli","Lancia"]},"Sahuagin Sacerdotessa":{"page":263,"type":"Umanoide","size":"Medio","subtype":"sahuagin","align":"legale malvagio","ac":"12 (armatura naturale)","hp":"33 (6d8 + 6)","speed":"9 m, nuotare 12 m","gs":"2","scores":[13,11,12,12,14,13],"traits":["Frenesia di Sangue","Anfibio Limitato","Telepatia con gli Squali","Incantesimi"],"actions":["Multiattacco","Morso","Artigli"]},"Sahuagin Barone":{"page":263,"type":"Umanoide","size":"Grande","subtype":"sahuagin","align":"legale malvagio","ac":"16 (corazza di piastre)","hp":"76 (9d10 + 27)","speed":"9 m, nuotare 15 m","gs":"5","scores":[19,15,16,14,13,17],"traits":["Frenesia di Sangue","Anfibio Limitato","Telepatia con gli Squali"],"actions":["Multiattacco","Morso","Artigli","Tridente"]},"Serpente di Fuoco":{"page":264,"type":"Elementale","size":"Medio","subtype":"","align":"neutrale malvagio","ac":"14 (armatura naturale)","hp":"22 (5d8)","speed":"9 m","gs":"1","scores":[12,14,11,7,10,8],"traits":["Corpo Surriscaldato"],"actions":["Multiattacco","Morso","Coda"]}}''')
SEALED = {name: (
    d["page"], d["type"], d["size"], d["subtype"], d["align"],
    d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
    tuple(d["traits"]), tuple(d["actions"]),
) for name, d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")


def audit(
    name: str, catalog: dict[str, Any] | None,
    existing_id: bool = False, same_named_monster: bool = False,
) -> dict[str, Any]:
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in required.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("not_an_original_statblock")
    d = MONSTERS[name]
    actual = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["traits"]), tuple(d["actions"]),
    )
    if actual != SEALED[name] or not 257 <= d["page"] <= 264:
        raise ValueError("original_source_fields_changed")
    m = HP_RE.fullmatch(d["hp"])
    if m is None:
        raise ValueError("invalid_hit_dice")
    avg, dice, sides, sign, mod = m.groups()
    adjustment = int(mod or 0) * (-1 if sign == "-" else 1)
    if int(avg) != int(dice) * (int(sides) + 1) // 2 + adjustment:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"]) != 6 or any(type(v) is not int or not 1 <= v <= 30 for v in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attrs = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "caratteristiche": dict(zip(("for", "des", "cos", "int", "sag", "car"),
                                    (str(x) for x in d["scores"]))),
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
