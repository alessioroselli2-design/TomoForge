"""Original Italian MM p289-296: five physical statblocks, no fake lore boxes.

Physical pages p293 (Unicorno lore) and p295-296 (Vampiro lore and lair)
do not contain an independent box. The vampire boxes begin p297. No
source scans or full licensed passages are stored; no Supabase writes.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Troglodita":{"page":289,"type":"Umanoide","size":"Medio","subtype":"troglodita","align":"caotico malvagio","ac":"11 (armatura naturale)","hp":"13 (2d8 + 4)","speed":"9 m","gs":"1/4","scores":[14,10,14,6,10,6],"traits":["Pelle Mimetica","Fetore","Sensibilità alla Luce del Sole"],"actions":["Multiattacco","Morso","Artiglio"],"legendary":[]},"Troll":{"page":290,"type":"Gigante","size":"Grande","subtype":"","align":"caotico malvagio","ac":"15 (armatura naturale)","hp":"84 (8d10 + 40)","speed":"9 m","gs":"5","scores":[18,13,20,7,9,7],"traits":["Olfatto Acuto","Rigenerazione"],"actions":["Multiattacco","Morso","Artiglio"],"legendary":[]},"Uccello Stigeo":{"page":291,"type":"Bestia","size":"Minuscolo","subtype":"","align":"senza allineamento","ac":"14 (armatura naturale)","hp":"2 (1d4)","speed":"3 m, volare 12 m","gs":"1/8","scores":[4,16,11,2,8,6],"traits":[],"actions":["Risucchio di Sangue"],"legendary":[]},"Umber Hulk":{"page":292,"type":"Mostruosità","size":"Grande","subtype":"","align":"caotico malvagio","ac":"18 (armatura naturale)","hp":"93 (11d10 + 33)","speed":"9 m, scavare 6 m","gs":"5","scores":[20,13,16,9,10,10],"traits":["Sguardo Confondente","Scavatore di Tunnel"],"actions":["Multiattacco","Artiglio","Mandibole"],"legendary":[]},"Unicorno":{"page":294,"type":"Celestiale","size":"Grande","subtype":"","align":"legale buono","ac":"12","hp":"67 (9d10 + 18)","speed":"15 m","gs":"5","scores":[18,14,15,11,17,16],"traits":["Carica","Incantesimi Innati","Resistenza alla Magia","Armi Magiche"],"actions":["Multiattacco","Zoccoli","Corno","Tocco Guaritore (3/Giorno)","Teletrasporto (1/Giorno)"],"legendary":["Zoccoli","Scudo Scintillante (Costa 2 Azioni)","Guarire Se Stesso (Costa 3 Azioni)"]}}''')
SEALED = {name: (
    d["page"], d["type"], d["size"], d["subtype"], d["align"],
    d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
    tuple(d["traits"]), tuple(d["actions"]), tuple(d["legendary"]),
) for name,d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")


def audit(name: str, catalog: dict[str, Any] | None,
          existing_id: bool = False, same_named_monster: bool = False) -> dict[str, Any]:
    expected = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILENAME,
        "physical_sha256": SHA256, "physical_pages": PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("not_an_original_statblock")
    d=MONSTERS[name]
    current=(
        d["page"],d["type"],d["size"],d["subtype"],d["align"],
        d["ac"],d["hp"],d["speed"],d["gs"],tuple(d["scores"]),
        tuple(d["traits"]),tuple(d["actions"]),tuple(d["legendary"]),
    )
    if current!=SEALED[name] or d["page"] not in (289,290,291,292,294):
        raise ValueError("source_fields_changed")
    match=HP_RE.fullmatch(d["hp"])
    if match is None:
        raise ValueError("invalid_hit_dice")
    avg,count,sides,sign,modifier=match.groups()
    bonus=int(modifier or 0)*(-1 if sign=="-" else 1)
    if int(avg)!=int(count)*(int(sides)+1)//2+bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"])!=6 or any(type(x) is not int or not 1<=x<=30 for x in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attrs={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],
        "velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":dict(zip(("for","des","cos","int","sag","car"),
                                   (str(x) for x in d["scores"]))),
        "tipo_creatura":d["type"],"taglia":d["size"],
        "sottotipo_creatura":d["subtype"],"allineamento":d["align"],
        "tratti_nomi_da_completare":list(d["traits"]),
        "azioni_nomi_da_completare":list(d["actions"]),
        "azioni_leggendarie_nomi_da_completare":list(d["legendary"]),
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt=(
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    identity=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {
        "id":"ref_"+hashlib.sha256(identity.encode()).hexdigest()[:32],
        "name":name,"physical_page":d["page"],"attributes":deepcopy(attrs),
        "source_excerpt":excerpt,"source_text_checksum":hashlib.sha256(excerpt.encode()).hexdigest(),
        "status":"source_checked_essential_statistics_only","writes":0,
    }
