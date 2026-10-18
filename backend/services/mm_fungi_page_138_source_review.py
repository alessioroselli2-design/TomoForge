"""Source review for three fungoid monster statblocks in Italian MM p138.

Careful: Spora Gassosa has negative hit-dice modifier (1d10 - 4), PF 1.
Unlike ordinary positive modifiers, this is canonical in the original scan.
No long manual text, original PDF, or DB writes are included.
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
HP_RE=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_SOURCE:dict[str,dict[str,Any]]={
    "Boleto Stridente": {
        "page": 138,
        "size": "Medio",
        "align": "senza allineamento",
        "ac": "5",
        "hp": "13 (3d8)",
        "speed": "0 m",
        "gs": "0",
        "scores": [
            1,
            1,
            10,
            1,
            3,
            1
        ]
    },
    "Fungo Viola": {
        "page": 138,
        "size": "Medio",
        "align": "senza allineamento",
        "ac": "5",
        "hp": "18 (4d8)",
        "speed": "1,5 m",
        "gs": "1/4",
        "scores": [
            3,
            1,
            10,
            1,
            3,
            1
        ]
    },
    "Spora Gassosa": {
        "page": 138,
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "5",
        "hp": "1 (1d10 - 4)",
        "speed": "0 m, volare 3 m (fluttuare)",
        "gs": "1/2",
        "scores": [
            5,
            1,
            3,
            1,
            1,
            1
        ]
    }
}
SOURCE_FIELDS={name:(d["page"],d["size"],d["align"],d["ac"],
                     d["hp"],d["speed"],d["gs"],tuple(d["scores"]))
               for name,d in _SOURCE.items()}
MONSTERS={name:dict(page=v[0],size=v[1],align=v[2],ac=v[3],hp=v[4],
                    speed=v[5],gs=v[6],scores=dict(zip(
                        ("for","des","cos","int","sag","car"),v[7])))
          for name,v in SOURCE_FIELDS.items()}

def audit(name:str,catalog:dict[str,Any]|None,
          existing_monster:bool=False)->dict[str,Any]:
    required={
        "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
        "physical_sha256":SHA256,"physical_pages":PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in required.items()):
        raise ValueError("unverified_pdf")
    if existing_monster:
        raise ValueError("monster_duplicate")
    if name not in SOURCE_FIELDS:
        raise ValueError("missing_source_box")
    d=MONSTERS[name]
    data=(d["page"],d["size"],d["align"],d["ac"],d["hp"],d["speed"],d["gs"],
          tuple(d["scores"][k] for k in ("for","des","cos","int","sag","car")))
    if data!=SOURCE_FIELDS[name]:
        raise ValueError("original_statblock_changed")
    hp=HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("unsupported_original_dice")
    avg,count,faces,op,diff=hp.groups()
    mod=(int(diff or 0)*(-1 if op=="-" else 1))
    if int(avg)!=int(count)*(int(faces)+1)//2+mod:
        raise ValueError("invalid_hit_dice_average")
    if any(not 1<=v<=30 for v in data[-1]):
        raise ValueError("six_scores_invalid")
    attrs={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],
        "velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":{k:str(v) for k,v in d["scores"].items()},
        "tipo_creatura":"Vegetale","taglia":d["size"],
        "allineamento":d["align"],"completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate")
    page=d["page"]
    identifier="ref_"+hashlib.sha256(
         f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}".encode()
    ).hexdigest()[:32]
    short=(f"{name}. Vegetale {d['size']}, {d['align']}. "
           f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
           f"Velocità {d['speed']}. Sfida {d['gs']}.")
    return {
        "id":identifier,"name":name,"physical_page":page,
        "source_excerpt":short,
        "source_text_checksum":hashlib.sha256(short.encode()).hexdigest(),
        "attributes":deepcopy(attrs),"status":"source_core_checked","writes":0,
    }
