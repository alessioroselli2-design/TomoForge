"""Read-only original Italian MM p133–136 creature statblock audit.

Four separately named original boxed statblocks verified from the private
licensed 353-page scan: Fatale dell'Acqua, Fauce Gorgogliante, Flumph, Fomorian.
Bigby Fomorian other/verified lore is not an existing monster-statblock
collision. Source-based core statistics only. This module performs no writes.
"""
from __future__ import annotations
import hashlib
import re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

SOURCE_ID="mm_2014_it"
FILENAME="847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256="b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES=353
HP=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")
_SOURCE:dict[str,list[Any]]={
    "Fatale Dell'Acqua": [
        133,
        "Elementale",
        "Grande",
        "neutrale",
        "13",
        "58 (9d10 + 9)",
        "0 m, nuotare 18 m",
        "3",
        [
            17,
            16,
            13,
            11,
            10,
            10
        ]
    ],
    "Fauce Gorgogliante": [
        134,
        "Aberrazione",
        "Media",
        "neutrale",
        "9",
        "67 (9d8 + 27)",
        "3 m, nuotare 3 m",
        "2",
        [
            10,
            8,
            16,
            3,
            10,
            6
        ]
    ],
    "Flumph": [
        135,
        "Aberrazione",
        "Piccola",
        "legale buono",
        "12",
        "7 (2d6)",
        "1,5 m, volare 9 m",
        "1/8",
        [
            6,
            15,
            10,
            14,
            14,
            11
        ]
    ],
    "Fomorian": [
        136,
        "Gigante",
        "Enorme",
        "caotico malvagio",
        "14 (armatura naturale)",
        "149 (13d12 + 65)",
        "9 m",
        "8",
        [
            23,
            10,
            20,
            9,
            14,
            6
        ]
    ]
}
SOURCE_FIELDS={name:(*data[:8],tuple(data[8])) for name,data in _SOURCE.items()}
MONSTERS={
 name:dict(page=v[0],type=v[1],size=v[2],align=v[3],ac=v[4],
           hp=v[5],speed=v[6],gs=v[7],
           abilities=dict(zip(("for","des","cos","int","sag","car"),v[8])))
 for name,v in SOURCE_FIELDS.items()
}

def audit(name:str,catalog:dict[str,Any]|None,
          duplicate_monster:bool=False)->dict[str,Any]:
    expected={
       "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
       "physical_sha256":SHA256,"physical_pages":PAGES,
       "source_status":"active","source_role":"authority",
       "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("original_source_not_authorized")
    if duplicate_monster:
        raise ValueError("duplicate_monster")
    if name not in SOURCE_FIELDS:
        raise ValueError("unknown_printed_statblock")
    d=MONSTERS[name]
    source_tuple=(d["page"],d["type"],d["size"],d["align"],d["ac"],
                  d["hp"],d["speed"],d["gs"],
                  tuple(d["abilities"][x] for x in ("for","des","cos","int","sag","car")))
    if source_tuple!=SOURCE_FIELDS[name]:
        raise ValueError("sealed_source_numbers_changed")
    parsed=HP.fullmatch(d["hp"])
    if parsed is None:
        raise ValueError("invalid_hit_dice")
    avg,num,faces,bonus=parsed.groups()
    if int(avg)!=int(num)*(int(faces)+1)//2+int(bonus or 0):
        raise ValueError("hit_dice_mean_error")
    if any(not 1<=score<=30 for score in source_tuple[-1]):
        raise ValueError("ability_score_out_of_range")
    attrs={
       "classe_armatura":d["ac"],"punti_ferita":d["hp"],
       "velocita":d["speed"],"grado_sfida":d["gs"],
       "caratteristiche":{k:str(v) for k,v in d["abilities"].items()},
       "tipo_creatura":d["type"],"taglia":d["size"],"allineamento":d["align"],
       "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate")
    page=d["page"]
    key=f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}"
    id="ref_"+hashlib.sha256(key.encode()).hexdigest()[:32]
    excerpt=(
       f"{name}. {d['type']} {d['size']}, {d['align']}. "
       f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
       f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    return {"id":id,"name":name,"physical_page":page,
            "source_excerpt":excerpt,
            "source_text_checksum":hashlib.sha256(excerpt.encode()).hexdigest(),
            "attributes":deepcopy(attrs),"status":"source_checked_core_only",
            "writes":0}
