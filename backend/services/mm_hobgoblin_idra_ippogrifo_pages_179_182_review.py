"""Five original Italian MM p179–182 independently boxed monster statblocks.

Owner-provided licensed 353-page scan, source file SHA256 registered.
One physical p179 has Hobgoblin and Hobgoblin Capitano boxes. The p180
Hobgoblin Signore della Guerra is a third distinct creature; p181 Idra
has multiple heads; p182 Ippogrifo is a mount-capable independent monster.
This audit covers only core stats and action/trait *names*; no full action
mechanics are asserted. No database writes or PDF assets are committed.
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
PDF_PAGES=353
HP_RE=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_ORIGINAL:dict[str,dict[str,Any]]={
    "Hobgoblin": {
        "page": 179,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "goblinoide",
        "align": "legale malvagio",
        "ac": "18 (cotta di maglia, scudo)",
        "hp": "11 (2d8 + 2)",
        "speed": "9 m",
        "gs": "1/2",
        "scores": [
            13,
            12,
            12,
            10,
            10,
            9
        ],
        "actions": [
            "Spada Lunga",
            "Arco Lungo"
        ]
    },
    "Hobgoblin Capitano": {
        "page": 179,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "goblinoide",
        "align": "legale malvagio",
        "ac": "17 (mezza armatura)",
        "hp": "39 (6d8 + 12)",
        "speed": "9 m",
        "gs": "3",
        "scores": [
            15,
            14,
            14,
            12,
            10,
            13
        ],
        "actions": [
            "Multiattacco",
            "Spadone",
            "Giavellotto",
            "Autorità"
        ]
    },
    "Hobgoblin Signore Della Guerra": {
        "page": 180,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "goblinoide",
        "align": "legale malvagio",
        "ac": "20 (armatura completa, scudo)",
        "hp": "97 (13d8 + 39)",
        "speed": "9 m",
        "gs": "6",
        "scores": [
            16,
            14,
            16,
            14,
            11,
            15
        ],
        "actions": [
            "Multiattacco",
            "Spada Lunga",
            "Scudo da Sfondamento",
            "Giavellotto",
            "Autorità",
            "Parata (reazione)"
        ]
    },
    "Idra": {
        "page": 181,
        "type": "Mostruosità",
        "size": "Enorme",
        "align": "senza allineamento",
        "ac": "15 (armatura naturale)",
        "hp": "172 (15d12 + 75)",
        "speed": "9 m, nuotare 9 m",
        "gs": "8",
        "scores": [
            20,
            12,
            20,
            2,
            10,
            7
        ],
        "actions": [
            "Multiattacco",
            "Morso"
        ],
        "traits": [
            "Trattenere il Respiro",
            "Teste Multiple",
            "Teste Reattive",
            "Sempre Sveglio"
        ]
    },
    "Ippogrifo": {
        "page": 182,
        "type": "Mostruosità",
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "11",
        "hp": "19 (3d10 + 3)",
        "speed": "12 m, volare 18 m",
        "gs": "1",
        "scores": [
            17,
            13,
            13,
            2,
            12,
            8
        ],
        "actions": [
            "Multiattacco",
            "Becco",
            "Artigli"
        ],
        "traits": [
            "Vista Acuta"
        ]
    }
}
SEALED={
 name:(d["page"],d["type"],d["size"],d.get("subtype",""),d["align"],d["ac"],
       d["hp"],d["speed"],d["gs"],tuple(d["scores"]),
       tuple(d["actions"]),tuple(d.get("traits",[])))
 for name,d in _ORIGINAL.items()
}
MONSTERS=deepcopy(_ORIGINAL)

def audit(name:str,catalog:dict[str,Any]|None,
          existing_id:bool=False,
          duplicate_monsters:list[dict[str,Any]]|None=None)->dict[str,Any]:
    required={
       "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
       "physical_sha256":SHA256,"physical_pages":PDF_PAGES,
       "source_status":"active","source_role":"authority",
       "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in required.items()):
        raise ValueError("original_source_authority_mismatch")
    if existing_id or duplicate_monsters:
        raise ValueError("existing_monster_duplicate")
    if name not in SEALED:
        raise ValueError("unrecognized_independent_statblock")
    d=MONSTERS[name]
    fields=(d["page"],d["type"],d["size"],d.get("subtype",""),d["align"],d["ac"],
            d["hp"],d["speed"],d["gs"],tuple(d["scores"]),
            tuple(d["actions"]),tuple(d.get("traits",[])))
    if fields!=SEALED[name]:
        raise ValueError("sealed_original_statblock_changed")
    hp=HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_hit_dice_source")
    avg,n,faces,op,bonus=hp.groups()
    signed=int(bonus or 0)*(-1 if op=="-" else 1)
    if int(avg)!=int(n)*(int(faces)+1)//2+signed:
        raise ValueError("hit_dice_average_mismatch")
    if len(d["scores"])!=6 or any(not isinstance(v,int) or not 1<=v<=30 for v in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attr={
       "classe_armatura":d["ac"],"punti_ferita":d["hp"],
       "velocita":d["speed"],"grado_sfida":d["gs"],
       "caratteristiche":dict(zip(("for","des","cos","int","sag","car"),
                                 (str(v) for v in d["scores"]))),
       "tipo_creatura":d["type"],"taglia":d["size"],
       "allineamento":d["align"],
       "azioni_nomi_da_completare":list(d["actions"]),
       "tratti_nomi_da_completare":list(d.get("traits",[])),
       "completezza_scheda":"statistiche_essenziali",
    }
    if d.get("subtype"):
        attr["sottotipo_creatura"]=d["subtype"]
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attr):
        raise ValueError("semantic_numeric_gate")
    page=d["page"]
    identity="ref_"+hashlib.sha256(
        f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}".encode()
    ).hexdigest()[:32]
    text=(f"{name}. {d['type']} {d['size']}, {d['align']}. "
          f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
          f"Velocità {d['speed']}. Sfida {d['gs']}.")
    return {
       "id":identity,"name":name,"physical_page":page,
       "source_excerpt":text,
       "source_text_checksum":hashlib.sha256(text.encode()).hexdigest(),
       "attributes":deepcopy(attr),
       "status":"source_checked_essential_statistics_only","writes":0,
    }
