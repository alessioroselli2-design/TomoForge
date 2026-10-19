"""Original source audit, Italian Monster Manual physical pp200–203.

Owner-provided scanned PDF independently viewed; verified 353-page source SHA.
Physical p201 is descriptive lore only, never a monster. Page 202 has three
separate named Maligno statblocks. This module does not mutate Supabase and
does not contain scans or full copyrighted ability/action descriptions.
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
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Magmin":{"page":200,"type":"Elementale","size":"Piccolo","subtype":"","align":"caotico neutrale","ac":"14 (armatura naturale)","hp":"9 (2d6 + 2)","speed":"9 m","gs":"1/2","scores":[7,15,12,8,11,10],"actions":["Tocco"],"traits":["Esplosione Mortale","Illuminazione Fiammeggiante"]},"Ago Maligno":{"page":202,"type":"Vegetale","size":"Medio","subtype":"","align":"neutrale malvagio","ac":"12 (armatura naturale)","hp":"11 (2d8 + 2)","speed":"9 m","gs":"1/4","scores":[12,12,13,4,8,3],"actions":["Artigli","Aghi"],"traits":[]},"Arbusto Maligno":{"page":202,"type":"Vegetale","size":"Piccolo","subtype":"","align":"neutrale malvagio","ac":"13 (armatura naturale)","hp":"4 (1d6 + 1)","speed":"6 m","gs":"1/8","scores":[6,13,12,4,8,3],"actions":["Artigli"],"traits":["Falso Aspetto"]},"Rampicante Maligno":{"page":202,"type":"Vegetale","size":"Medio","subtype":"","align":"neutrale malvagio","ac":"12 (armatura naturale)","hp":"26 (4d8 + 8)","speed":"3 m","gs":"1/2","scores":[15,8,14,5,10,3],"actions":["Stritolare","Vegetali Intralcanti (Ricarica 5-6)"],"traits":["Falso Aspetto"]},"Manticora":{"page":203,"type":"Mostruosità","size":"Grande","subtype":"","align":"legale malvagio","ac":"14 (armatura naturale)","hp":"68 (8d10 + 24)","speed":"9 m, volare 15 m","gs":"3","scores":[17,16,17,7,12,8],"actions":["Multiattacco","Morso","Artigli","Aculei Caudali"],"traits":["Ricrescita degli Aculei Caudali"]}}''')
SEALED = {
    name: (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["actions"]), tuple(d["traits"]),
    )
    for name, d in _SOURCE.items()
}
MONSTERS = deepcopy(_SOURCE)


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    existing_id: bool = False,
    same_named_monster: bool = False,
) -> dict[str, Any]:
    """Fail closed for authority, duplicates, tampering or core stat mismatch."""
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
    if not isinstance(catalog, dict) or any(
        catalog.get(k) != v for k, v in expected.items()
    ):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("not_an_independent_source_statblock")
    d = MONSTERS[name]
    fields = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["actions"]), tuple(d["traits"]),
    )
    if fields != SEALED[name]:
        raise ValueError("original_source_fields_changed")
    if d["page"] not in (200, 202, 203):
        raise ValueError("outside_statblock_pages")
    hp = HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_hit_dice")
    average, count, sides, sign, modifier = hp.groups()
    bonus = int(modifier or 0) * (-1 if sign == "-" else 1)
    if int(average) != int(count) * (int(sides) + 1) // 2 + bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"]) != 6 or any(
        not isinstance(v, int) or not 1 <= v <= 30 for v in d["scores"]
    ):
        raise ValueError("six_ability_scores_invalid")
    attrs = {
        "classe_armatura": d["ac"],
        "punti_ferita": d["hp"],
        "velocita": d["speed"],
        "grado_sfida": d["gs"],
        "caratteristiche": dict(zip(
            ("for", "des", "cos", "int", "sag", "car"),
            (str(v) for v in d["scores"]),
        )),
        "tipo_creatura": d["type"],
        "taglia": d["size"],
        "sottotipo_creatura": d["subtype"],
        "allineamento": d["align"],
        "azioni_nomi_da_completare": list(d["actions"]),
        "tratti_nomi_da_completare": list(d["traits"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    excerpt = (
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    return {
        "id": "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32],
        "name": name,
        "physical_page": d["page"],
        "source_excerpt": excerpt,
        "source_text_checksum": hashlib.sha256(excerpt.encode()).hexdigest(),
        "attributes": deepcopy(attrs),
        "status": "source_checked_essential_statistics_only",
        "writes": 0,
    }
