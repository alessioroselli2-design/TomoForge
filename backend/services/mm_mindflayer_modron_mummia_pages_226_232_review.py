"""Read-only original-source review: MM Mind Flayer, Minotaur, Modron, Mummy.

Physical pp225 and 231 are lore/lair; no autonomous statblocks. Mind Flayer
Arcanista and Modron Fuori Controllo are variants, not duplicate base entries.
Only numerical fields and headings, never licensed complete passages/scans.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Mind Flayer":{"page":226,"type":"Aberrazione","size":"Media","subtype":"","align":"legale malvagio","ac":"15 (corazza di piastre)","hp":"71 (13d8 + 13)","speed":"9 m","gs":"7","scores":[11,12,12,19,17,17],"traits":["Resistenza alla Magia","Incantesimi Innati (Psionici)"],"actions":["Tentacoli","Estrarre Cervello","Assalto Mentale (Ricarica 5-6)"],"variants":["Mind Flayer Arcanista (GS 8; variante incantatrice non statblock autonomo)"]},"Minotauro":{"page":227,"type":"Mostruosità","size":"Grande","subtype":"","align":"caotico malvagio","ac":"14 (armatura naturale)","hp":"76 (9d10 + 27)","speed":"12 m","gs":"3","scores":[18,11,16,6,16,9],"traits":["Carica","Ricordo Labirintico","Avventato"],"actions":["Ascia Bipenne","Incornata"],"variants":[]},"Monodrone":{"page":228,"type":"Costrutto","size":"Medio","subtype":"","align":"legale neutrale","ac":"15 (armatura naturale)","hp":"5 (1d8 + 1)","speed":"9 m, volare 9 m","gs":"1/8","scores":[10,13,12,4,10,5],"traits":["Mente Assiomatica","Disintegrazione"],"actions":["Pugnale","Giavellotto"],"variants":["Modron Fuori Controllo (variante allineamento, non statblock)"]},"Duodrone":{"page":229,"type":"Costrutto","size":"Medio","subtype":"","align":"legale neutrale","ac":"15 (armatura naturale)","hp":"11 (2d8 + 2)","speed":"9 m","gs":"1/4","scores":[11,13,12,6,10,7],"traits":["Mente Assiomatica","Disintegrazione"],"actions":["Multiattacco","Pugno","Giavellotto"],"variants":[]},"Tridrone":{"page":229,"type":"Costrutto","size":"Medio","subtype":"","align":"legale neutrale","ac":"15 (armatura naturale)","hp":"16 (3d8 + 3)","speed":"9 m","gs":"1/2","scores":[12,13,12,9,10,9],"traits":["Mente Assiomatica","Disintegrazione"],"actions":["Multiattacco","Pugno","Giavellotto"],"variants":[]},"Quadrone":{"page":230,"type":"Costrutto","size":"Medio","subtype":"","align":"legale neutrale","ac":"16 (armatura naturale)","hp":"22 (4d8 + 4)","speed":"9 m, volare 9 m","gs":"1","scores":[12,14,12,10,10,11],"traits":["Mente Assiomatica","Disintegrazione"],"actions":["Multiattacco","Pugno","Arco Corto"],"variants":[]},"Pentadrone":{"page":230,"type":"Costrutto","size":"Grande","subtype":"","align":"legale neutrale","ac":"16 (armatura naturale)","hp":"32 (5d10 + 5)","speed":"12 m","gs":"2","scores":[15,14,12,10,10,13],"traits":["Mente Assiomatica","Disintegrazione"],"actions":["Multiattacco","Braccio","Gas Paralizzante (Ricarica 5-6)"],"variants":[]},"Mummia":{"page":232,"type":"Non morto","size":"Medio","subtype":"","align":"legale malvagio","ac":"11 (armatura naturale)","hp":"58 (9d8 + 18)","speed":"6 m","gs":"3","scores":[16,8,15,6,10,12],"traits":[],"actions":["Multiattacco","Pugno di Putrefazione","Sguardo Funesto"],"variants":[]}}''')
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")


def _sealed_fields(d: dict[str, Any]) -> tuple[Any, ...]:
    return (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["traits"]), tuple(d["actions"]), tuple(d["variants"]),
    )


SEALED = {name: _sealed_fields(d) for name, d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)


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
        raise ValueError("not_a_source_statblock")
    d = MONSTERS[name]
    if _sealed_fields(d) != SEALED[name] or d["page"] not in (226, 227, 228, 229, 230, 232):
        raise ValueError("original_source_fields_changed")
    hp = HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_hit_dice")
    avg, count, sides, sign, modifier = hp.groups()
    bonus = int(modifier or 0) * (-1 if sign == "-" else 1)
    if int(avg) != (int(count) * (int(sides) + 1)) // 2 + bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"]) != 6 or any(type(v) is not int or not 1 <= v <= 30 for v in d["scores"]):
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
        "azioni_leggendarie_nomi_da_completare": [],
        "tratti_nomi_da_completare": list(d["traits"]),
        "varianti_nomi_da_completare": list(d["variants"]),
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
        "name": name,
        "physical_page": d["page"],
        "source_excerpt": excerpt,
        "source_text_checksum": hashlib.sha256(excerpt.encode()).hexdigest(),
        "attributes": deepcopy(attrs),
        "status": "source_checked_essential_statistics_only",
        "writes": 0,
    }
