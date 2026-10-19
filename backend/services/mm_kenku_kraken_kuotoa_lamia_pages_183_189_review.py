"""Italian MM p183–189: six independent licensed-source monster statblocks.

Owner-provided licensed 353-page scanned PDF, full-file SHA-256 matched to
active authority. Physical p184 contains Kraken lore without statblock; p185
contains the Kraken box. Physical p186 Kuo-Toa lore only; p187 base Kuo-Toa,
p188 two independent specialist boxes. Compact core fields and action/trait
TITLES ONLY. Kraken legendary mechanics and priest spells are NOT yet
transcribed in full. No DB writes and no licensed PDF pages committed.
"""
from __future__ import annotations
import hashlib
import re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags,monster_semantic_numeric_flags
SOURCE_ID="mm_2014_it"
FILENAME="847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256="b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES=353
HP_RE=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_ORIGINAL:dict[str,dict[str,Any]]={
    "Kenku": {
        "page": 183,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "kenku",
        "align": "caotico neutrale",
        "ac": "13",
        "hp": "13 (3d8)",
        "speed": "9 m",
        "gs": "1/4",
        "scores": [
            10,
            16,
            10,
            11,
            10,
            10
        ],
        "actions": [
            "Spada Corta",
            "Arco Corto"
        ],
        "traits": [
            "Imboscata",
            "Imitare"
        ]
    },
    "Kraken": {
        "page": 185,
        "type": "Mostruosità",
        "size": "Mastodontica",
        "subtype": "titano",
        "align": "caotico malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "472 (27d20 + 189)",
        "speed": "6 m, nuotare 18 m",
        "gs": "23",
        "scores": [
            30,
            11,
            25,
            22,
            18,
            20
        ],
        "actions": [
            "Multiattacco",
            "Morso",
            "Tentacoli",
            "Scagliare",
            "Tempesta di Fulmini"
        ],
        "traits": [
            "Anfibio",
            "Libertà di Movimento",
            "Mostro da Assedio",
            "Azioni Leggendarie"
        ]
    },
    "Kuo-Toa": {
        "page": 187,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "kuo-toa",
        "align": "neutrale malvagio",
        "ac": "13 (armatura naturale, scudo)",
        "hp": "18 (4d8)",
        "speed": "9 m, nuotare 9 m",
        "gs": "1/4",
        "scores": [
            13,
            10,
            11,
            11,
            10,
            8
        ],
        "actions": [
            "Morso",
            "Lancia",
            "Rete"
        ],
        "traits": [
            "Anfibio",
            "Percezione Ultraterrena",
            "Sgusciante",
            "Sensibilità alla Luce del Sole"
        ]
    },
    "Kuo-Toa Gran Sacerdote": {
        "page": 188,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "kuo-toa",
        "align": "neutrale malvagio",
        "ac": "13 (armatura naturale)",
        "hp": "97 (13d8 + 39)",
        "speed": "9 m, nuotare 9 m",
        "gs": "6",
        "scores": [
            16,
            14,
            16,
            13,
            16,
            14
        ],
        "actions": [
            "Multiattacco",
            "Scettro",
            "Colpo Senz'Armi"
        ],
        "traits": [
            "Anfibio",
            "Percezione Ultraterrena",
            "Sgusciante",
            "Sensibilità alla Luce del Sole",
            "Incantesimi"
        ]
    },
    "Kuo-Toa Esecutore": {
        "page": 188,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "kuo-toa",
        "align": "neutrale malvagio",
        "ac": "11 (armatura naturale)",
        "hp": "65 (10d8 + 20)",
        "speed": "9 m, nuotare 9 m",
        "gs": "1",
        "scores": [
            14,
            10,
            14,
            12,
            14,
            11
        ],
        "actions": [
            "Multiattacco",
            "Morso",
            "Bastone Tenaglia"
        ],
        "traits": [
            "Anfibio",
            "Percezione Ultraterrena",
            "Sgusciante",
            "Sensibilità alla Luce del Sole",
            "Incantesimi"
        ]
    },
    "Lamia": {
        "page": 189,
        "type": "Mostruosità",
        "size": "Grande",
        "align": "caotico malvagio",
        "ac": "13 (armatura naturale)",
        "hp": "97 (13d10 + 26)",
        "speed": "9 m",
        "gs": "4",
        "scores": [
            16,
            13,
            15,
            14,
            15,
            16
        ],
        "actions": [
            "Multiattacco",
            "Artigli",
            "Pugnale",
            "Tocco Intossicante"
        ],
        "traits": [
            "Incantesimi Innati"
        ]
    }
}
SEALED={
 n:(d["page"],d["type"],d["size"],d.get("subtype",""),d["align"],
    d["ac"],d["hp"],d["speed"],d["gs"],tuple(d["scores"]),
    tuple(d["actions"]),tuple(d["traits"]))
 for n,d in _ORIGINAL.items()
}
MONSTERS=deepcopy(_ORIGINAL)

def audit(name:str,catalog:dict[str,Any]|None,
          existing_id:bool=False,
          same_name_monsters:list[dict[str,Any]]|None=None)->dict[str,Any]:
    required={
      "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
      "physical_sha256":SHA256,"physical_pages":PAGES,
      "source_status":"active","source_role":"authority",
      "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in required.items()):
        raise ValueError("source_catalog_mismatch")
    if existing_id or same_name_monsters:
        raise ValueError("duplicate_monster")
    if name not in SEALED:
        raise ValueError("no_independent_statblock")
    d=MONSTERS[name]
    current=(d["page"],d["type"],d["size"],d.get("subtype",""),d["align"],
             d["ac"],d["hp"],d["speed"],d["gs"],tuple(d["scores"]),
             tuple(d["actions"]),tuple(d["traits"]))
    if current!=SEALED[name]:
        raise ValueError("original_source_fields_changed")
    h=HP_RE.fullmatch(d["hp"])
    if h is None:
        raise ValueError("unparseable_hit_dice")
    mean,n,sides,op,val=h.groups()
    bonus=int(val or 0)*(-1 if op=="-" else 1)
    if int(mean)!=int(n)*(int(sides)+1)//2+bonus:
        raise ValueError("hit_dice_arithmetic_failed")
    if len(d["scores"])!=6 or any(not isinstance(x,int) or not 1<=x<=30 for x in d["scores"]):
        raise ValueError("six_scores_invalid")
    attr={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],
        "velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":dict(zip(
          ("for","des","cos","int","sag","car"),(str(x) for x in d["scores"]))),
        "tipo_creatura":d["type"],"taglia":d["size"],"allineamento":d["align"],
        "azioni_nomi_da_completare":list(d["actions"]),
        "tratti_nomi_da_completare":list(d["traits"]),
        "completezza_scheda":"statistiche_essenziali",
    }
    if d.get("subtype"):
        attr["sottotipo_creatura"]=d["subtype"]
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attr):
        raise ValueError("semantic_numeric_or_identity_gate")
    page=d["page"]
    key=f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}"
    short=(f"{name}. {d['type']} {d['size']}, {d['align']}. "
           f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
           f"Velocità {d['speed']}. Sfida {d['gs']}.")
    return {
        "id":"ref_"+hashlib.sha256(key.encode()).hexdigest()[:32],
        "name":name,"physical_page":page,
        "source_excerpt":short,
        "source_text_checksum":hashlib.sha256(short.encode()).hexdigest(),
        "attributes":deepcopy(attr),
        "status":"original_source_core_only","writes":0,
    }
