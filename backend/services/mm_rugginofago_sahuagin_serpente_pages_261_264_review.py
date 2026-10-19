"""Direct visual-source audit of five Italian MM monsters on pp261–264.

The Salamandra illustration/lore on p264 is not an extra statblock:
Serpente di Fuoco is the independent box, Salamandra follows later.
Full text/images are not stored; no DB writes.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Rugginofago":{"page":261,"type":"Mostruosità","size":"Medio","subtype":"","align":"senza allineamento","ac":"14 (armatura naturale)","hp":"27 (5d8 + 5)","speed":"12 m","gs":"1/2","scores":[13,12,13,2,13,6],"traits":["Fiutare il Ferro","Arrugginire"],"actions":["Morso","Antenne"]},"Sahuagin":{"page":262,"type":"Umanoide","size":"Medio","subtype":"sahuagin","align":"legale malvagio","ac":"12 (armatura naturale)","hp":"22 (4d8 + 4)","speed":"9 m, nuotare 12 m","gs":"1/2","scores":[13,11,12,12,13,9],"traits":["Frenesia di Sangue","Anfibio Limitato","Telepatia con gli Squali"],"actions":["Multiattacco","Morso","Artigli","Lancia"]},"Sahuagin Sacerdotessa":{"page":263,"type":"Umanoide","size":"Medio","subtype":"sahuagin","align":"legale malvagio","ac":"12 (armatura naturale)","hp":"33 (6d8 + 6)","speed":"9 m, nuotare 12 m","gs":"2","scores":[13,11,12,12,14,13],"traits":["Frenesia di Sangue","Anfibio Limitato","Telepatia con gli Squali","Incantesimi"],"actions":["Multiattacco","Morso","Artigli"]},"Sahuagin Barone":{"page":263,"type":"Umanoide","size":"Grande","subtype":"sahuagin","align":"legale malvagio","ac":"16 (corazza di piastre)","hp":"76 (9d10 + 27)","speed":"9 m, nuotare 15 m","gs":"5","scores":[19,15,16,14,13,17],"traits":["Frenesia di Sangue","Anfibio Limitato","Telepatia con gli Squali"],"actions":["Multiattacco","Morso","Artigli","Tridente"]},"Serpente di Fuoco":{"page":264,"type":"Elementale","size":"Medio","subtype":"","align":"neutrale malvagio","ac":"14 (armatura naturale)","hp":"22 (5d8)","speed":"9 m","gs":"1","scores":[12,14,11,7,10,8],"traits":["Corpo Surriscaldato"],"actions":["Multiattacco","Morso","Coda"]}}''')
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
    expected = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in expected.items()):
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
    if fields != SEALED[name] or d["page"] not in (261, 262, 263, 264):
        raise ValueError("source_fields_changed")
    hp = HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_hit_dice")
    avg, count, sides, sign, modifier = hp.groups()
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
        "attributes": deepcopy(attrs),
        "source_excerpt": excerpt,
        "source_text_checksum": hashlib.sha256(excerpt.encode()).hexdigest(),
        "status": "source_checked_essential_statistics_only", "writes": 0,
    }
