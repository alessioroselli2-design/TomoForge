"""Original MM Italian p173–177 source audit: six boxed monster statblocks.

Human visual read from the owner's private 353-page scanned Monster Manual,
registered SHA-256 corroborated. Original printed p174 has both Grick and
Grick Alfa as independent boxes. Data are the compact core (AC/HP/speed/
six scores/challenge) and mere action titles, not full feature transcription.
Nothing here touches the database or publishes copyrighted source pages.
"""
from __future__ import annotations

import hashlib
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
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_ORIGINAL: dict[str,dict[str,Any]] = {
    "Grell": {
        "page": 173,
        "type": "Aberrazione",
        "size": "Media",
        "align": "neutrale malvagio",
        "ac": "12",
        "hp": "55 (10d8 + 10)",
        "speed": "3 m, volare 9 m (fluttuare)",
        "gs": "3",
        "scores": [
            15,
            14,
            13,
            12,
            11,
            9
        ],
        "actions": [
            "Multiattacco",
            "Tentacoli",
            "Becco"
        ]
    },
    "Grick": {
        "page": 174,
        "type": "Mostruosità",
        "size": "Media",
        "align": "neutrale",
        "ac": "14 (armatura naturale)",
        "hp": "27 (6d8)",
        "speed": "9 m, scalare 9 m",
        "gs": "2",
        "scores": [
            14,
            14,
            11,
            3,
            14,
            5
        ],
        "actions": [
            "Multiattacco",
            "Tentacoli",
            "Becco"
        ]
    },
    "Grick Alfa": {
        "page": 174,
        "type": "Mostruosità",
        "size": "Grande",
        "align": "neutrale",
        "ac": "18 (armatura naturale)",
        "hp": "75 (10d10 + 20)",
        "speed": "9 m, scalare 9 m",
        "gs": "7",
        "scores": [
            18,
            16,
            15,
            4,
            14,
            9
        ],
        "actions": [
            "Multiattacco",
            "Coda",
            "Tentacoli",
            "Becco"
        ]
    },
    "Grifone": {
        "page": 175,
        "type": "Mostruosità",
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "12",
        "hp": "59 (7d10 + 21)",
        "speed": "9 m, volare 24 m",
        "gs": "2",
        "scores": [
            18,
            15,
            16,
            2,
            13,
            8
        ],
        "actions": [
            "Multiattacco",
            "Becco",
            "Artigli"
        ]
    },
    "Grimlock": {
        "page": 176,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "grimlock",
        "align": "neutrale malvagio",
        "ac": "11",
        "hp": "11 (2d8 + 2)",
        "speed": "9 m",
        "gs": "1/4",
        "scores": [
            16,
            12,
            12,
            9,
            8,
            6
        ],
        "actions": [
            "Randello Chiodato"
        ]
    },
    "Guardiano Protettore": {
        "page": 177,
        "type": "Costrutto",
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "17 (armatura naturale)",
        "hp": "142 (15d10 + 60)",
        "speed": "9 m",
        "gs": "7",
        "scores": [
            18,
            8,
            18,
            7,
            10,
            3
        ],
        "actions": [
            "Multiattacco",
            "Pugno",
            "Protettore (reazione)"
        ]
    }
}
SEALED = {
    name: (
        d["page"],d["type"],d["size"],d.get("subtype",""),d["align"],
        d["ac"],d["hp"],d["speed"],d["gs"],
        tuple(d["scores"]),tuple(d["actions"]),
    )
    for name,d in _ORIGINAL.items()
}
MONSTERS = deepcopy(_ORIGINAL)


def audit(name:str,catalog:dict[str,Any]|None,
          existing_id:bool=False,
          existing_same_name_monsters:list[dict[str,Any]]|None=None)->dict[str,Any]:
    required={
        "logical_source_id":SOURCE_ID,
        "physical_filename":FILENAME,
        "physical_sha256":SHA256,
        "physical_pages":PAGES,
        "source_status":"active",
        "source_role":"authority",
        "authority_class":"licensed_translation",
        "text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in required.items()):
        raise ValueError("registered_source_mismatch")
    if existing_id or existing_same_name_monsters:
        raise ValueError("monster_duplicate")
    if name not in SEALED:
        raise ValueError("unrecognized_source_statblock")
    d=MONSTERS[name]
    fields=(
        d["page"],d["type"],d["size"],d.get("subtype",""),d["align"],
        d["ac"],d["hp"],d["speed"],d["gs"],
        tuple(d["scores"]),tuple(d["actions"]),
    )
    if fields!=SEALED[name]:
        raise ValueError("sealed_original_values_modified")
    match=HP_RE.fullmatch(d["hp"])
    if match is None:
        raise ValueError("invalid_hp_source")
    avg,count,faces,op,val=match.groups()
    mod=int(val or 0)*(-1 if op=="-" else 1)
    if int(avg)!=int(count)*(int(faces)+1)//2+mod:
        raise ValueError("original_hp_math_failed")
    if len(d["scores"])!=6 or any(not isinstance(v,int) or not 1<=v<=30 for v in d["scores"]):
        raise ValueError("abilities_invalid")
    attrs={
        "classe_armatura":d["ac"],
        "punti_ferita":d["hp"],
        "velocita":d["speed"],
        "grado_sfida":d["gs"],
        "caratteristiche":dict(zip(
            ("for","des","cos","int","sag","car"),(str(v) for v in d["scores"]))),
        "tipo_creatura":d["type"],
        "taglia":d["size"],
        "allineamento":d["align"],
        "azioni_nomi_da_completare":list(d["actions"]),
        "completezza_scheda":"statistiche_essenziali",
    }
    if d.get("subtype"):
        attrs["sottotipo_creatura"]=d["subtype"]
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_identity_or_numeric_failure")
    page=d["page"]
    key=f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}"
    brief=(
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    return {
        "id":"ref_"+hashlib.sha256(key.encode()).hexdigest()[:32],
        "name":name,
        "physical_page":page,
        "source_excerpt":brief,
        "source_text_checksum":hashlib.sha256(brief.encode()).hexdigest(),
        "attributes":deepcopy(attrs),
        "status":"source_core_checked_only",
        "writes":0,
    }
