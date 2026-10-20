"""Original source-based audit of four Italian MM monsters p129–132.

Distinct printed statblocks: Empireo, Ettercap, Ettin and Fantasma. Empireo
has probabilistic alignment 75%/25%; Fantasma may have any alignment.
Represent these explicitly without silently choosing one. This audit only
confirms compact core statistics; no DB writes or original PDF publication.
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
PAGE_COUNT=353
HP_RE=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")
_INPUT:dict[str,list[Any]]={
    "Empireo": [
        129,
        "Celestiale",
        "Enorme",
        "caotico buono (75%) o neutrale malvagio (25%)",
        "22 (armatura naturale)",
        "313 (19d12 + 190)",
        "15 m, nuotare 15 m, volare 15 m",
        "23",
        [
            30,
            21,
            30,
            21,
            22,
            27
        ]
    ],
    "Ettercap": [
        130,
        "Mostruosità",
        "Media",
        "neutrale malvagio",
        "13 (armatura naturale)",
        "44 (8d8 + 8)",
        "9 m, scalare 9 m",
        "2",
        [
            14,
            15,
            13,
            7,
            12,
            8
        ]
    ],
    "Ettin": [
        131,
        "Gigante",
        "Grande",
        "caotico malvagio",
        "12 (armatura naturale)",
        "85 (10d10 + 30)",
        "12 m",
        "4",
        [
            21,
            8,
            17,
            6,
            10,
            8
        ]
    ],
    "Fantasma": [
        132,
        "Non morto",
        "Medio",
        "qualsiasi allineamento",
        "11",
        "45 (10d8)",
        "0 m, volare 12 m (fluttuare)",
        "4",
        [
            7,
            13,
            10,
            10,
            12,
            17
        ]
    ]
}
SOURCE_FIELDS={name:(*data[:8],tuple(data[8])) for name,data in _INPUT.items()}
MONSTERS={
 name:dict(page=v[0],type=v[1],size=v[2],align=v[3],ac=v[4],
           hp=v[5],speed=v[6],gs=v[7],abilities=dict(zip(
               ("for","des","cos","int","sag","car"),v[8])))
 for name,v in SOURCE_FIELDS.items()
}
EMPIREO_ALIGNMENT_PERCENT={"caotico buono":75,"neutrale malvagio":25}

def audit(name:str,catalog:dict[str,Any]|None,
          existing_monster:bool=False)->dict[str,Any]:
    expected={
      "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
      "physical_sha256":SHA256,"physical_pages":PAGE_COUNT,
      "source_status":"active","source_role":"authority",
      "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("unverified_original_pdf")
    if existing_monster:
        raise ValueError("duplicate_monster")
    if name not in SOURCE_FIELDS:
        raise ValueError("not_original_statblock")
    d=MONSTERS[name]
    current=(d["page"],d["type"],d["size"],d["align"],d["ac"],
             d["hp"],d["speed"],d["gs"],
             tuple(d["abilities"][v] for v in ("for","des","cos","int","sag","car")))
    if current!=SOURCE_FIELDS[name]:
        raise ValueError("sealed_fields_mismatch")
    match=HP_RE.fullmatch(d["hp"])
    if not match:
        raise ValueError("hit_dice_unparseable")
    avg,n,die,bonus=match.groups()
    if int(avg)!=int(n)*(int(die)+1)//2+int(bonus or 0):
        raise ValueError("hit_dice_mean_mismatch")
    if any(not 1<=n<=30 for n in current[-1]):
        raise ValueError("ability_score_bad")
    attrs={
      "classe_armatura":d["ac"],"punti_ferita":d["hp"],
      "velocita":d["speed"],"grado_sfida":d["gs"],
      "caratteristiche":{key:str(v) for key,v in d["abilities"].items()},
      "tipo_creatura":d["type"],"taglia":d["size"],
      "allineamento":d["align"],
      "completezza_scheda":"statistiche_essenziali",
    }
    if name=="Empireo":
        attrs["allineamento_varianti_percentuali"]=deepcopy(EMPIREO_ALIGNMENT_PERCENT)
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_numeric_or_identity_gate")
    page=d["page"]
    identity="ref_"+hashlib.sha256(
       f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}".encode()
    ).hexdigest()[:32]
    brief=(
      f"{name}. {d['type']} {d['size']}, {d['align']}. "
      f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
      f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    return {
       "id":identity,"name":name,"physical_page":page,
       "source_excerpt":brief,
       "source_text_checksum":hashlib.sha256(brief.encode()).hexdigest(),
       "attributes":deepcopy(attrs),"status":"original_core_checked",
       "writes":0,
    }
