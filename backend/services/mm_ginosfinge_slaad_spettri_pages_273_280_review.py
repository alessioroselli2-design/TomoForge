"""Italian MM original p273–280: Ginosfinge, six Slaad, Spaventapasseri and Spettro.

Physical pages 274-275 are Slaad lore/art, not separate statistics blocks.
Each entry below is a source-checked *core* statblock, not full licensed prose.
No source scans or database mutations are stored in the repository.
"""
from __future__ import annotations
import hashlib
import json
import re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES = 353
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Ginosfinge":{"page":273,"type":"Mostruosità","size":"Grande","subtype":"","align":"legale neutrale","ac":"17 (armatura naturale)","hp":"136 (16d10 + 48)","speed":"12 m, volare 18 m","gs":"11","scores":[18,15,16,18,18,18],"traits":["Imperscrutabile","Armi Magiche","Incantesimi"],"actions":["Multiattacco","Artiglio"],"legendary":["Attacco con Artiglio","Teletrasporto (Costa 2 Azioni)","Lanciare un Incantesimo (Costa 3 Azioni)"]},"Slaad Girino":{"page":276,"type":"Aberrazione","size":"Minuscola","subtype":"","align":"caotico neutrale","ac":"12","hp":"10 (4d4)","speed":"9 m","gs":"1/8","scores":[7,15,10,3,5,3],"traits":["Resistenza alla Magia"],"actions":["Morso"],"legendary":[]},"Slaad Rosso":{"page":276,"type":"Aberrazione","size":"Grande","subtype":"","align":"caotico neutrale","ac":"14 (armatura naturale)","hp":"93 (11d10 + 33)","speed":"9 m","gs":"5","scores":[16,12,16,6,6,7],"traits":["Resistenza alla Magia","Rigenerazione"],"actions":["Multiattacco","Morso","Artiglio"],"legendary":[]},"Slaad Blu":{"page":276,"type":"Aberrazione","size":"Grande","subtype":"","align":"caotico neutrale","ac":"15 (armatura naturale)","hp":"123 (13d10 + 52)","speed":"9 m","gs":"7","scores":[20,15,18,7,7,9],"traits":["Resistenza alla Magia","Rigenerazione"],"actions":["Multiattacco","Morso","Artiglio"],"legendary":[]},"Slaad Verde":{"page":277,"type":"Aberrazione","size":"Grande","subtype":"mutaforma","align":"caotico neutrale","ac":"16 (armatura naturale)","hp":"127 (15d10 + 45)","speed":"9 m","gs":"8","scores":[18,15,16,11,8,12],"traits":["Mutaforma","Incantesimi Innati","Resistenza alla Magia","Rigenerazione"],"actions":["Multiattacco","Morso (Solo Forma di Slaad)","Artiglio (Solo Forma di Slaad)","Bastone","Scagliare Fiamma"],"legendary":[]},"Slaad Grigio":{"page":277,"type":"Aberrazione","size":"Medio","subtype":"mutaforma","align":"caotico neutrale","ac":"18 (armatura naturale)","hp":"127 (17d8 + 51)","speed":"9 m","gs":"9","scores":[17,17,16,13,8,14],"traits":["Mutaforma","Incantesimi Innati","Resistenza alla Magia","Armi Magiche","Rigenerazione"],"actions":["Multiattacco","Morso (Solo Forma di Slaad)","Artigli (Solo Forma di Slaad)","Spadone"],"legendary":[]},"Slaad della Morte":{"page":278,"type":"Aberrazione","size":"Medio","subtype":"mutaforma","align":"caotico neutrale","ac":"18 (armatura naturale)","hp":"170 (20d8 + 80)","speed":"9 m","gs":"10","scores":[20,15,19,15,10,16],"traits":["Mutaforma","Incantesimi Innati","Resistenza alla Magia","Armi Magiche","Rigenerazione"],"actions":["Multiattacco","Morso (Solo Forma di Slaad)","Artigli (Solo Forma di Slaad)","Spadone"],"legendary":[]},"Spaventapasseri":{"page":279,"type":"Costrutto","size":"Medio","subtype":"","align":"caotico malvagio","ac":"11","hp":"36 (8d8)","speed":"9 m","gs":"1","scores":[11,13,11,10,10,13],"traits":["Falso Aspetto"],"actions":["Multiattacco","Artiglio","Sguardo Terrificante"],"legendary":[]},"Spettro":{"page":280,"type":"Non morto","size":"Medio","subtype":"","align":"caotico malvagio","ac":"12","hp":"22 (5d8)","speed":"0 m, volare 15 m (fluttuare)","gs":"1","scores":[1,14,11,10,10,11],"traits":["Movimento Incorporeo","Sensibilità alla Luce del Sole"],"actions":["Risucchio di Vita"],"legendary":[]}}''')
SEALED = {n: (
    d["page"], d["type"], d["size"], d["subtype"], d["align"],
    d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
    tuple(d["traits"]), tuple(d["actions"]), tuple(d["legendary"]),
) for n, d in _SOURCE.items()}
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
    fields = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["traits"]), tuple(d["actions"]), tuple(d["legendary"]),
    )
    if fields != SEALED[name] or d["page"] not in (273, 276, 277, 278, 279, 280):
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
