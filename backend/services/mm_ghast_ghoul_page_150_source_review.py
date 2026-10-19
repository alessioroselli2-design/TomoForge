"""Separate physical MM p150 Ghast and Ghoul source-proofed core blocks.

User-owned licensed Italian PDF (353 pages); original physical page 150 has
two separately boxed statblocks. Names, CA, HP, speed, six scores, GS and
action labels were visually checked. Complete effects/action prose remains
out of scope. No changes to existing records or database writes.
"""
from __future__ import annotations
import hashlib
import re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PDF_PAGES = 353
HP = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")
_ORIGINAL:dict[str,dict[str,Any]] = {
    "Ghast": {
        "page": 150,
        "type": "Non morto",
        "size": "Medio",
        "align": "caotico malvagio",
        "ac": "13",
        "hp": "36 (8d8)",
        "speed": "9 m",
        "gs": "2",
        "scores": [
            16,
            17,
            10,
            11,
            10,
            8
        ],
        "actions": [
            "Morso",
            "Artigli"
        ]
    },
    "Ghoul": {
        "page": 150,
        "type": "Non morto",
        "size": "Medio",
        "align": "caotico malvagio",
        "ac": "12",
        "hp": "22 (5d8)",
        "speed": "9 m",
        "gs": "1",
        "scores": [
            13,
            15,
            10,
            7,
            10,
            6
        ],
        "actions": [
            "Morso",
            "Artigli"
        ]
    }
}
SEALED = {
 name: (d["page"],d["type"],d["size"],d["align"],d["ac"],d["hp"],
        d["speed"],d["gs"],tuple(d["scores"]),tuple(d["actions"]))
 for name,d in _ORIGINAL.items()
}
MONSTERS = deepcopy(_ORIGINAL)

def audit(name:str,catalog:dict[str,Any]|None,
          id_exists:bool=False,monster_duplicates:list[dict[str,Any]]|None=None)->dict[str,Any]:
    expected={
       "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
       "physical_sha256":SHA256,"physical_pages":PDF_PAGES,
       "source_status":"active","source_role":"authority",
       "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("invalid_authoritative_source")
    if id_exists or monster_duplicates:
        raise ValueError("duplicate_monster")
    if name not in SEALED:
        raise ValueError("not_a_source_statblock")
    d=MONSTERS[name]
    actual=(d["page"],d["type"],d["size"],d["align"],d["ac"],d["hp"],
            d["speed"],d["gs"],tuple(d["scores"]),tuple(d["actions"]))
    if actual!=SEALED[name]:
        raise ValueError("sealed_original_modified")
    hp=HP.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("bad_hit_dice")
    avg,n,die,plus=hp.groups()
    if int(avg)!=int(n)*(int(die)+1)//2+int(plus or 0):
        raise ValueError("hit_dice_math_mismatch")
    if len(d["scores"])!=6 or any(not 1<=s<=30 for s in d["scores"]):
        raise ValueError("abilities_out_of_range")
    attrs={
       "classe_armatura":d["ac"],"punti_ferita":d["hp"],
       "velocita":d["speed"],"grado_sfida":d["gs"],
       "caratteristiche":dict(zip(("for","des","cos","int","sag","car"),(str(s) for s in d["scores"]))),
       "tipo_creatura":d["type"],"taglia":d["size"],"allineamento":d["align"],
       "azioni_nomi_da_completare":list(d["actions"]),
       "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate")
    token=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    summary=(f"{name}. {d['type']} {d['size']}, {d['align']}. "
             f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
             f"Velocità {d['speed']}. Sfida {d['gs']}.")
    return {
       "id":"ref_"+hashlib.sha256(token.encode()).hexdigest()[:32],
       "name":name,"physical_page":d["page"],"source_excerpt":summary,
       "source_text_checksum":hashlib.sha256(summary.encode()).hexdigest(),
       "attributes":deepcopy(attrs),"writes":0,"status":"source_checked_core_only",
    }
