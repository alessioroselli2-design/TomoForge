"""Original Italian Monster Manual physical pp236–240: six statblocks.

Full scanned-source SHA256 independently checked with active authority;
only short labels and essential statistics stored; no page images or DB writes.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Nothic":{"page":236,"type":"Aberrazione","size":"Medio","align":"neutrale malvagio","ac":"15 (armatura naturale)","hp":"45 (6d8 + 18)","speed":"9 m","gs":"2","scores":[14,16,16,13,10,8],"traits":["Vista Acuta"],"actions":["Multiattacco","Artiglio","Sguardo Marcescente","Intuizione Innaturale"]},"Armatura Animata":{"page":237,"type":"Costrutto","size":"Medio","align":"senza allineamento","ac":"18 (armatura naturale)","hp":"33 (6d8 + 6)","speed":"7,5 m","gs":"1","scores":[14,11,13,1,3,1],"traits":["Suscettibilità all'Anti-magia","Falso Aspetto"],"actions":["Multiattacco","Schianto"]},"Spada Volante":{"page":238,"type":"Costrutto","size":"Piccolo","align":"senza allineamento","ac":"17 (armatura naturale)","hp":"17 (5d6)","speed":"0 m, volare 15 m (fluttuare)","gs":"1/4","scores":[12,15,11,1,5,1],"traits":["Suscettibilità all'Anti-magia","Falso Aspetto"],"actions":["Spada Lunga"]},"Tappeto Soffocante":{"page":238,"type":"Costrutto","size":"Grande","align":"senza allineamento","ac":"12","hp":"33 (6d10)","speed":"3 m","gs":"2","scores":[17,14,10,1,3,1],"traits":["Suscettibilità all'Anti-magia","Trasferire Danni","Falso Aspetto"],"actions":["Soffocare"]},"Ogre":{"page":239,"type":"Gigante","size":"Grande","align":"caotico malvagio","ac":"11 (armatura di pelle)","hp":"59 (7d10 + 21)","speed":"12 m","gs":"2","scores":[19,8,16,5,7,7],"traits":[],"actions":["Randello Pesante","Giavellotto"]},"Mezzogre":{"page":240,"type":"Gigante","size":"Grande","align":"qualsiasi allineamento caotico","ac":"12 (armatura di pelle)","hp":"30 (4d10 + 8)","speed":"9 m","gs":"1","scores":[17,10,14,7,9,10],"traits":[],"actions":["Ascia da Battaglia","Giavellotto"]}}''')
SEALED = {n: (
    d["page"], d["type"], d["size"], d["align"], d["ac"], d["hp"],
    d["speed"], d["gs"], tuple(d["scores"]), tuple(d["traits"]),
    tuple(d["actions"]),
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
        d["speed"], d["gs"], tuple(d["scores"]), tuple(d["traits"]), tuple(d["actions"]),
    )
    if current != SEALED[name] or d["page"] not in (236, 237, 238, 239, 240):
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
