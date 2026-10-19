"""Italian Monster Manual p265–272: seven verified core statblocks; one overlap.

Physical page 267 Scheletro is already verified in the Player's Handbook,
same AC and HP. Avoid inserting it twice; cross-source full-field concordance
not yet certified. p271 is sphinx lore, not a monster statblock.
No original scans nor full copyrighted mechanics committed; no DB writes.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Salamandra":{"page":265,"type":"Elementale","size":"Grande","subtype":"","align":"neutrale malvagio","ac":"15 (armatura naturale)","hp":"90 (12d10 + 24)","speed":"9 m","gs":"5","scores":[18,14,15,11,10,12],"traits":["Corpo Surriscaldato","Armi Surriscaldate"],"actions":["Multiattacco","Lancia","Coda"],"legendary":[]},"Satiro":{"page":266,"type":"Folletto","size":"Medio","subtype":"","align":"caotico neutrale","ac":"14 (armatura di cuoio)","hp":"31 (7d8)","speed":"12 m","gs":"1/2","scores":[12,16,11,12,10,14],"traits":["Resistenza alla Magia"],"actions":["Sfondamento","Spada Corta","Arco Corto"],"legendary":[]},"Scheletro Minotauro":{"page":268,"type":"Non morto","size":"Grande","subtype":"","align":"legale malvagio","ac":"12 (armatura naturale)","hp":"67 (9d10 + 18)","speed":"12 m","gs":"2","scores":[18,11,15,6,8,5],"traits":["Carica"],"actions":["Ascia Bipenne","Incornata"],"legendary":[]},"Scheletro Cavallo da Guerra":{"page":268,"type":"Non morto","size":"Grande","subtype":"","align":"legale malvagio","ac":"13 (frammenti di bardatura)","hp":"22 (3d10 + 6)","speed":"18 m","gs":"1/2","scores":[18,12,15,2,8,5],"traits":[],"actions":["Zoccoli"],"legendary":[]},"Sciacallo Mannaro":{"page":269,"type":"Umanoide","size":"Medio","subtype":"mutaforma","align":"caotico malvagio","ac":"12","hp":"18 (4d8)","speed":"12 m","gs":"1/2","scores":[11,15,11,13,11,10],"traits":["Mutaforma","Olfatto e Udito Acuti","Tattiche del Branco"],"actions":["Morso (Solo Forma di Sciacallo o Ibrida)","Scimitarra (Solo Forma Umana o Ibrida)","Sguardo Soporifero"],"legendary":[]},"Segugio Infernale":{"page":270,"type":"Immondo","size":"Medio","subtype":"","align":"legale malvagio","ac":"15 (armatura naturale)","hp":"45 (7d8 + 14)","speed":"15 m","gs":"3","scores":[17,12,14,6,13,6],"traits":["Olfatto e Udito Acuti","Tattiche del Branco"],"actions":["Morso","Soffio di Fuoco (Ricarica 5-6)"],"legendary":[]},"Androsfinge":{"page":272,"type":"Mostruosità","size":"Grande","subtype":"","align":"legale neutrale","ac":"17 (armatura naturale)","hp":"199 (19d10 + 95)","speed":"12 m, volare 18 m","gs":"17","scores":[22,10,20,16,18,23],"traits":["Imperscrutabile","Armi Magiche","Incantesimi"],"actions":["Multiattacco","Artiglio","Ruggito (3/Giorno)"],"legendary":["Attacco con Artiglio","Teletrasporto (Costa 2 Azioni)","Lanciare un Incantesimo (Costa 3 Azioni)"]}}''')
_DUPLICATE: dict[str, Any] = json.loads(r'''{"name":"Scheletro","page":267,"existing_source_key":"Manuale_del_giocatore__1787259882002.pdf","existing_page":null,"verified_ca":"13 (frammenti di armatura)","verified_hp":"13 (2d8 + 4)","cross_source_reuse":true,"not_confirmed_full_fields":true}''')
SEALED = {n: (
    d["page"], d["type"], d["size"], d["subtype"], d["align"],
    d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
    tuple(d["traits"]), tuple(d["actions"]), tuple(d["legendary"]),
) for n, d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)
CROSS_SOURCE_OVERLAP = deepcopy(_DUPLICATE)
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
    if name == _DUPLICATE["name"]:
        raise ValueError("already_verified_cross_source")
    if name not in SEALED:
        raise ValueError("not_an_original_statblock")
    d = MONSTERS[name]
    fields = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["traits"]), tuple(d["actions"]), tuple(d["legendary"]),
    )
    if fields != SEALED[name] or d["page"] not in (265, 266, 268, 269, 270, 272):
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
        "classe_armatura": d["ac"],
        "punti_ferita": d["hp"],
        "velocita": d["speed"],
        "grado_sfida": d["gs"],
        "caratteristiche": dict(zip(
            ("for", "des", "cos", "int", "sag", "car"),
            (str(s) for s in d["scores"]),
        )),
        "tipo_creatura": d["type"], "taglia": d["size"],
        "sottotipo_creatura": d["subtype"], "allineamento": d["align"],
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
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {
        "id": "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32],
        "name": name, "physical_page": d["page"],
        "attributes": deepcopy(attrs), "source_excerpt": excerpt,
        "source_text_checksum": hashlib.sha256(excerpt.encode()).hexdigest(),
        "status": "source_checked_essential_statistics_only", "writes": 0,
    }
