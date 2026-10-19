"""Source-gated gnolls, svirfneblin and goblins: Italian Monster Manual p164-167.

Original licensed 353-page image-only PDF visually inspected at high
resolution. p164 has THREE gnoll boxes, one of which is an Immondo rather
than an Umanoide. p165 holds one small gnome box; p166 is Goblin lore only,
and p167 has TWO separately boxed goblins. Core-only; actions are names,
not the complete action mechanics. No DB writes, no PDF material committed.
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
PAGES = 353
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_ORIGINAL: dict[str, dict[str, Any]] = {
    "Gnoll": {
        "page": 164,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "gnoll",
        "align": "caotico malvagio",
        "ac": "15 (armatura di pelle, scudo)",
        "hp": "22 (5d8)",
        "speed": "9 m",
        "gs": "1/2",
        "scores": [
            14,
            12,
            11,
            6,
            10,
            7
        ],
        "actions": [
            "Morso",
            "Lancia",
            "Arco Lungo"
        ]
    },
    "Gnoll Signore Del Branco": {
        "page": 164,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "gnoll",
        "align": "caotico malvagio",
        "ac": "15 (giaco di maglia)",
        "hp": "49 (9d8 + 9)",
        "speed": "9 m",
        "gs": "2",
        "scores": [
            16,
            14,
            13,
            8,
            11,
            9
        ],
        "actions": [
            "Multiattacco",
            "Morso",
            "Falcione",
            "Arco Lungo",
            "Incitare Furia"
        ]
    },
    "Gnoll Zanna Di Yeenoghu": {
        "page": 164,
        "type": "Immondo",
        "size": "Medio",
        "subtype": "gnoll",
        "align": "caotico malvagio",
        "ac": "14 (armatura di pelle)",
        "hp": "65 (10d8 + 20)",
        "speed": "9 m",
        "gs": "4",
        "scores": [
            17,
            15,
            15,
            10,
            11,
            13
        ],
        "actions": [
            "Multiattacco",
            "Morso",
            "Artiglio"
        ]
    },
    "Gnomo Delle Profondità (Svirfneblin)": {
        "page": 165,
        "type": "Umanoide",
        "size": "Piccolo",
        "subtype": "gnomo",
        "align": "neutrale buono",
        "ac": "15 (giaco di maglia)",
        "hp": "16 (3d6 + 6)",
        "speed": "6 m",
        "gs": "1/2",
        "scores": [
            15,
            14,
            14,
            12,
            10,
            9
        ],
        "actions": [
            "Piccone da Guerra",
            "Dardo Avvelenato"
        ]
    },
    "Goblin": {
        "page": 167,
        "type": "Umanoide",
        "size": "Piccolo",
        "subtype": "goblinoide",
        "align": "neutrale malvagio",
        "ac": "15 (armatura di cuoio, scudo)",
        "hp": "7 (2d6)",
        "speed": "9 m",
        "gs": "1/4",
        "scores": [
            8,
            14,
            10,
            10,
            8,
            8
        ],
        "actions": [
            "Scimitarra",
            "Arco Corto"
        ]
    },
    "Goblin Capo": {
        "page": 167,
        "type": "Umanoide",
        "size": "Piccolo",
        "subtype": "goblinoide",
        "align": "neutrale malvagio",
        "ac": "17 (giaco di maglia, scudo)",
        "hp": "21 (6d6)",
        "speed": "9 m",
        "gs": "1",
        "scores": [
            10,
            14,
            10,
            10,
            8,
            10
        ],
        "actions": [
            "Multiattacco",
            "Scimitarra",
            "Giavellotto",
            "Sviare Attacco (reazione)"
        ]
    }
}
SEALED = {
    name: (v["page"],v["type"],v["size"],v["subtype"],v["align"],v["ac"],
           v["hp"],v["speed"],v["gs"],tuple(v["scores"]),tuple(v["actions"]))
    for name,v in _ORIGINAL.items()
}
MONSTERS = deepcopy(_ORIGINAL)


def audit(name: str, catalog: dict[str, Any] | None,
          duplicate_id: bool=False,
          duplicate_monsters: list[dict[str, Any]] | None=None) -> dict[str, Any]:
    authority = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILENAME,
        "physical_sha256": SHA256, "physical_pages": PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in authority.items()):
        raise ValueError("unregistered_original_source")
    if duplicate_id or duplicate_monsters:
        raise ValueError("monster_duplicate")
    if name not in SEALED:
        raise ValueError("not_a_named_original_monster")
    d=MONSTERS[name]
    fields=(d["page"],d["type"],d["size"],d["subtype"],d["align"],d["ac"],
            d["hp"],d["speed"],d["gs"],tuple(d["scores"]),tuple(d["actions"]))
    if fields!=SEALED[name]:
        raise ValueError("sealed_source_drift")
    hp=HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_hit_dice_expression")
    avg,n,die,op,diff=hp.groups()
    adj=int(diff or 0)*(-1 if op=="-" else 1)
    if int(avg)!=int(n)*(int(die)+1)//2+adj:
        raise ValueError("incorrect_hit_dice_average")
    if len(d["scores"])!=6 or any(
        not isinstance(v,int) or not 1<=v<=30 for v in d["scores"]
    ):
        raise ValueError("six_abilities_invalid")
    attrs={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],
        "velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":dict(zip(("for","des","cos","int","sag","car"),
                                   (str(v) for v in d["scores"]))),
        "tipo_creatura":d["type"],"taglia":d["size"],
        "sottotipo_creatura":d["subtype"],
        "allineamento":d["align"],
        "azioni_nomi_da_completare":list(d["actions"]),
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    p=d["page"]
    key=f"{SOURCE_ID}|{FILENAME}|{p}|{name.casefold()}"
    text=(f"{name}. {d['type']} {d['size']} ({d['subtype']}), {d['align']}. "
          f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
          f"Velocità {d['speed']}. Sfida {d['gs']}.")
    return {"id":"ref_"+hashlib.sha256(key.encode()).hexdigest()[:32],
            "name":name,"physical_page":p,"source_excerpt":text,
            "source_text_checksum":hashlib.sha256(text.encode()).hexdigest(),
            "attributes":deepcopy(attrs),"writes":0,
            "status":"source_checked_core_only"}
