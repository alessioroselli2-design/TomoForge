"""Bounded source audit, original Italian MM physical pages 118–121.

p118 Drago Fatato: one source block with TWO challenge ratings by colour;
its card is deliberately marked *blocked* pending safe multi-variant schema.
p119 Driade, p120 Drider, p121 Duergar have independent boxed monster
statblocks. Existing Duergar lore / ability in other manuals is NOT a
same-type monster duplicate. No database writes.
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
HP = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")
_BASE: dict[str, list[Any]] = {
    "Driade": [
        119,
        "Folletto",
        "Medio",
        "neutrale",
        "11 (16 con pelle coriacea)",
        "22 (5d8)",
        "9 m",
        "1",
        [
            10,
            12,
            11,
            14,
            15,
            18
        ]
    ],
    "Drider": [
        120,
        "Mostruosità",
        "Grande",
        "caotico malvagio",
        "19 (armatura naturale)",
        "123 (13d10 + 52)",
        "9 m, scalare 9 m",
        "6",
        [
            16,
            16,
            18,
            13,
            14,
            12
        ]
    ],
    "Duergar": [
        121,
        "Umanoide",
        "Medio",
        "legale malvagio",
        "16 (corazza di scaglie, scudo)",
        "26 (4d8 + 8)",
        "7,5 m",
        "1",
        [
            14,
            11,
            14,
            11,
            10,
            9
        ]
    ]
}
SOURCE_FIELDS = {name: (*v[:8], tuple(v[8])) for name,v in _BASE.items()}
MONSTERS = {
 name: dict(page=v[0],type=v[1],size=v[2],align=v[3],ac=v[4],
            hp=v[5],speed=v[6],gs=v[7],abilities=dict(zip(
                ("for","des","cos","int","sag","car"),v[8])))
 for name,v in SOURCE_FIELDS.items()
}
VARIANT_DRAGON = {
    "name": "Drago Fatato",
    "physical_page": 118,
    "challenge_by_colour": {
        "rosso": "1", "arancione": "1", "giallo": "1",
        "verde": "2", "blu": "2", "indaco": "2", "viola": "2",
    },
    "statblock": {
        "size": "Minuscolo",
        "type": "Drago",
        "alignment": "caotico buono",
        "ac": "15", "hp": "14 (4d4 + 4)",
        "speed": "3 m, volare 18 m",
        "ability_scores": (3,20,13,14,12,16),
    },
}

def audit(name: str, catalog: dict[str, Any] | None,
          existing_monster: bool = False) -> dict[str, Any]:
    expected = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILENAME,
        "physical_sha256": SHA256, "physical_pages": PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("registered_source_not_authorized")
    if existing_monster:
        raise ValueError("duplicate_monster")
    if name == VARIANT_DRAGON["name"]:
        return {
            "name":name,"physical_page":118,
            "challenge_by_colour":deepcopy(VARIANT_DRAGON["challenge_by_colour"]),
            "source_core":deepcopy(VARIANT_DRAGON["statblock"]),
            "status":"blocked_multi_challenge_rating_requires_explicit_variant_schema",
            "writes":0,
        }
    if name not in SOURCE_FIELDS:
        raise ValueError("not_named_monster_statblock")
    d=MONSTERS[name]
    fields=(d["page"],d["type"],d["size"],d["align"],d["ac"],d["hp"],
            d["speed"],d["gs"],tuple(d["abilities"][x] for x in
               ("for","des","cos","int","sag","car")))
    if fields!=SOURCE_FIELDS[name]:
        raise ValueError("source_fields_changed")
    m=HP.fullmatch(d["hp"])
    if m is None:
        raise ValueError("unsupported_hit_dice")
    avg,n,die,bonus=m.groups()
    if int(avg)!=int(n)*(int(die)+1)//2+int(bonus or 0):
        raise ValueError("hit_dice_math")
    if any(not 1 <= v <= 30 for v in fields[-1]):
        raise ValueError("incomplete_six_ability_scores")
    attr={
       "classe_armatura":d["ac"], "punti_ferita":d["hp"],
       "velocita":d["speed"], "grado_sfida":d["gs"],
       "caratteristiche":{k:str(v) for k,v in d["abilities"].items()},
       "tipo_creatura":d["type"], "taglia":d["size"],
       "allineamento":d["align"],
       "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attr):
        raise ValueError("global_monster_gate")
    page=d["page"]
    sid="ref_"+hashlib.sha256(
         f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}".encode()
    ).hexdigest()[:32]
    summary=(
       f"{name}. {d['type']} {d['size']}, {d['align']}. "
       f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
       f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    return {
       "id":sid,"name":name,"physical_page":page,
       "source_excerpt":summary,
       "source_text_checksum":hashlib.sha256(summary.encode()).hexdigest(),
       "attributes":deepcopy(attr),"writes":0,
       "status":"source_verified_core_only",
    }
