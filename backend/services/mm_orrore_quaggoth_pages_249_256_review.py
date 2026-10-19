"""Italian MM pp249–256: seven new boxes and one existing cross-source match.

Pseudodrago physical p255 was independently compared to the verified PHB
record, for AC/HP/speed; do NOT insert a duplicate. No scans, full text,
or database writes in this audit.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Orrore Uncinato":{"page":249,"type":"Mostruosità","size":"Grande","subtype":"","align":"neutrale","ac":"15 (armatura naturale)","hp":"75 (10d10 + 20)","speed":"9 m, scalare 9 m","gs":"3","scores":[18,10,15,6,12,7],"traits":["Senso Radar","Udito Acuto"],"actions":["Multiattacco","Uncino"]},"Orsogufo":{"page":250,"type":"Mostruosità","size":"Grande","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"59 (7d10 + 21)","speed":"12 m","gs":"3","scores":[20,12,17,3,12,7],"traits":["Vista e Olfatto Acuti"],"actions":["Multiattacco","Becco","Artigli"]},"Otyugh":{"page":251,"type":"Aberrazione","size":"Grande","subtype":"","align":"neutrale","ac":"14 (armatura naturale)","hp":"114 (12d10 + 48)","speed":"9 m","gs":"5","scores":[16,11,19,6,13,6],"traits":["Telepatia Limitata"],"actions":["Multiattacco","Morso","Tentacolo","Schianto con Tentacolo"]},"Pegaso":{"page":252,"type":"Celestiale","size":"Grande","subtype":"","align":"caotico buono","ac":"12","hp":"59 (7d10 + 21)","speed":"18 m, volare 27 m","gs":"2","scores":[18,15,16,10,15,13],"traits":[],"actions":["Zoccoli"]},"Peryton":{"page":253,"type":"Mostruosità","size":"Medio","subtype":"","align":"caotico malvagio","ac":"13 (armatura naturale)","hp":"33 (6d8 + 6)","speed":"6 m, volare 18 m","gs":"2","scores":[16,12,13,9,12,10],"traits":["Attacco in Picchiata","Volo Sfuggente","Vista e Olfatto Acuti"],"actions":["Multiattacco","Incornata","Speroni"]},"Pixie":{"page":254,"type":"Folletto","size":"Minuscolo","subtype":"","align":"neutrale buono","ac":"15","hp":"1 (1d4 - 1)","speed":"3 m, volare 9 m","gs":"1/4","scores":[2,20,8,10,14,15],"traits":["Resistenza alla Magia","Incantesimi Innati"],"actions":["Invisibilità Superiore"]},"Quaggoth":{"page":256,"type":"Umanoide","size":"Medio","subtype":"quaggoth","align":"caotico neutrale","ac":"13 (armatura naturale)","hp":"45 (6d8 + 18)","speed":"9 m, scalare 9 m","gs":"2","scores":[17,12,16,6,12,7],"traits":["Furia del Ferimento"],"actions":["Multiattacco","Artiglio"]}}''')
_CROSS_SOURCE_OVERLAP: dict[str, Any] = json.loads(r'''{"name":"Pseudodrago","page":255,"existing_source_key":"Manuale_del_giocatore__1787259882002.pdf","existing_source_page":308,"shared_core":{"classe_armatura":"13 (armatura naturale)","punti_ferita":"7 (2d4 + 2)","velocita":"4,5 m, volare 18 m"},"decision":"reuse_existing_verified_monster_no_duplicate","verified_against_full_record":false}''')
SEALED = {n: (
    d["page"], d["type"], d["size"], d["subtype"], d["align"],
    d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
    tuple(d["traits"]), tuple(d["actions"]),
) for n, d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)
CROSS_SOURCE_OVERLAP = deepcopy(_CROSS_SOURCE_OVERLAP)
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
    if name == "Pseudodrago":
        raise ValueError("existing_cross_source_same_core_stats")
    if name not in SEALED:
        raise ValueError("not_an_original_statblock")
    d = MONSTERS[name]
    fields = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["traits"]), tuple(d["actions"]),
    )
    if fields != SEALED[name] or d["page"] not in (249, 250, 251, 252, 253, 254, 256):
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
