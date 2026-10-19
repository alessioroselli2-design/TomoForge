"""Eight original-source statblocks, Italian MM physical pages 241–248.

Pages 244–245 are lore on Orcs and no autonomous statblock. Each variant has
its own actual source box. Full licensed texts are not stored in repository.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Ombra":{"page":241,"type":"Non morto","size":"Medio","subtype":"","align":"caotico malvagio","ac":"12","hp":"16 (3d8 + 3)","speed":"12 m","gs":"1/2","scores":[6,14,13,6,10,8],"traits":["Amorfo","Furtività d'Ombra","Debolezza alla Luce del Sole"],"actions":["Risucchio di Forza"]},"Omuncolo":{"page":242,"type":"Costrutto","size":"Minuscolo","subtype":"","align":"neutrale","ac":"13 (armatura naturale)","hp":"5 (2d4)","speed":"6 m, volare 12 m","gs":"0","scores":[4,15,11,10,10,7],"traits":["Legame Telepatico"],"actions":["Morso"]},"Oni":{"page":243,"type":"Gigante","size":"Grande","subtype":"","align":"legale malvagio","ac":"16 (cotta di maglia)","hp":"110 (13d10 + 39)","speed":"9 m, volare 9 m","gs":"7","scores":[19,11,16,14,12,15],"traits":["Incantesimi Innati","Armi Magiche","Rigenerazione"],"actions":["Multiattacco","Artiglio (Solo Forma di Oni)","Falcione","Cambiare Forma"]},"Orco":{"page":246,"type":"Umanoide","size":"Medio","subtype":"orco","align":"caotico malvagio","ac":"13 (armatura di pelle)","hp":"15 (2d8 + 6)","speed":"9 m","gs":"1/2","scores":[16,12,16,7,11,10],"traits":["Aggressivo"],"actions":["Ascia Bipenne","Giavellotto"]},"Orco Capotribù Guerriero":{"page":246,"type":"Umanoide","size":"Medio","subtype":"orco","align":"caotico malvagio","ac":"16 (cotta di maglia)","hp":"93 (11d8 + 44)","speed":"9 m","gs":"4","scores":[18,12,18,11,11,16],"traits":["Aggressivo","Furia di Gruumsh"],"actions":["Multiattacco","Ascia Bipenne","Lancia","Grido di Battaglia (1/Giorno)"]},"Orco Occhio di Gruumsh":{"page":247,"type":"Umanoide","size":"Medio","subtype":"orco","align":"caotico malvagio","ac":"16 (corazza ad anelli, scudo)","hp":"45 (6d8 + 18)","speed":"9 m","gs":"2","scores":[16,12,16,9,13,12],"traits":["Aggressivo","Furia di Gruumsh","Incantesimi"],"actions":["Lancia"]},"Orog":{"page":247,"type":"Umanoide","size":"Medio","subtype":"orco","align":"caotico malvagio","ac":"18 (armatura completa)","hp":"42 (5d8 + 20)","speed":"9 m","gs":"2","scores":[18,12,18,12,11,12],"traits":["Aggressivo"],"actions":["Multiattacco","Ascia Bipenne","Giavellotto"]},"Orrore Corazzato":{"page":248,"type":"Costrutto","size":"Medio","subtype":"","align":"neutrale","ac":"20 (armatura completa, scudo)","hp":"60 (8d8 + 24)","speed":"9 m, volare 9 m","gs":"4","scores":[18,13,16,10,10,10],"traits":["Resistenza alla Magia","Immunità agli Incantesimi"],"actions":["Multiattacco","Spada Lunga"]}}''')
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
    if fields != SEALED[name] or d["page"] not in (241, 242, 243, 246, 247, 248):
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
