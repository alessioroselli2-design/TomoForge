"""Source audit: four golems + Gorgone, original Italian MM p169–172.

Original 353-page image-only owner licensed PDF visually checked at high
resolution. Page 168 contains descriptive golem lore. Page 171 contains
two separate boxed constructs. CA/PF/speed/GS/scores are core-only;
action names are labels, not certified full action/spell descriptions.
No DB mutations or copyrighted PDF assets in this module.
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
    "Golem Di Argilla": {
        "page": 169,
        "type": "Costrutto",
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "14 (armatura naturale)",
        "hp": "133 (14d10 + 56)",
        "speed": "6 m",
        "gs": "9",
        "scores": [
            20,
            9,
            18,
            3,
            8,
            1
        ],
        "actions": [
            "Multiattacco",
            "Schianto",
            "Velocità"
        ]
    },
    "Golem Di Carne": {
        "page": 170,
        "type": "Costrutto",
        "size": "Medio",
        "align": "neutrale",
        "ac": "9",
        "hp": "93 (11d8 + 44)",
        "speed": "9 m",
        "gs": "5",
        "scores": [
            19,
            9,
            18,
            6,
            10,
            5
        ],
        "actions": [
            "Multiattacco",
            "Schianto"
        ]
    },
    "Golem Di Ferro": {
        "page": 171,
        "type": "Costrutto",
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "20 (armatura naturale)",
        "hp": "210 (20d10 + 100)",
        "speed": "9 m",
        "gs": "16",
        "scores": [
            24,
            9,
            20,
            3,
            11,
            1
        ],
        "actions": [
            "Multiattacco",
            "Schianto",
            "Spada",
            "Soffio di Veleno"
        ]
    },
    "Golem Di Pietra": {
        "page": 171,
        "type": "Costrutto",
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "17 (armatura naturale)",
        "hp": "178 (17d10 + 85)",
        "speed": "9 m",
        "gs": "10",
        "scores": [
            22,
            9,
            20,
            3,
            11,
            1
        ],
        "actions": [
            "Multiattacco",
            "Schianto",
            "Lentezza"
        ]
    },
    "Gorgone": {
        "page": 172,
        "type": "Mostruosità",
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "19 (armatura naturale)",
        "hp": "114 (12d10 + 48)",
        "speed": "12 m",
        "gs": "5",
        "scores": [
            20,
            11,
            18,
            2,
            12,
            7
        ],
        "actions": [
            "Corno",
            "Zoccoli",
            "Soffio Pietrificante"
        ]
    }
}
SEALED = {
    n: (d["page"], d["type"], d["size"], d["align"], d["ac"], d["hp"],
        d["speed"], d["gs"], tuple(d["scores"]), tuple(d["actions"]))
    for n, d in _ORIGINAL.items()
}
MONSTERS = deepcopy(_ORIGINAL)

def audit(name: str, catalog: dict[str, Any] | None,
          existing_monster: bool = False) -> dict[str, Any]:
    required = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILENAME,
        "physical_sha256": SHA256, "physical_pages": PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in required.items()):
        raise ValueError("source_authority_mismatch")
    if existing_monster:
        raise ValueError("already_imported_monster")
    if name not in SEALED:
        raise ValueError("not_original_box")
    d = MONSTERS[name]
    current = (
        d["page"],d["type"],d["size"],d["align"],d["ac"],d["hp"],
        d["speed"],d["gs"],tuple(d["scores"]),tuple(d["actions"]),
    )
    if current != SEALED[name]:
        raise ValueError("sealed_source_fields_changed")
    m=HP_RE.fullmatch(d["hp"])
    if m is None:
        raise ValueError("hit_dice_not_parseable")
    avg,n,sides,sign,modifier=m.groups()
    mod=int(modifier or 0)*(-1 if sign=="-" else 1)
    if int(avg)!=int(n)*(int(sides)+1)//2+mod:
        raise ValueError("hit_points_average_incorrect")
    if len(d["scores"])!=6 or any(not isinstance(v,int) or not 1<=v<=30 for v in d["scores"]):
        raise ValueError("six_abilities_invalid")
    attrs = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "caratteristiche": dict(zip(("for","des","cos","int","sag","car"),(str(x) for x in d["scores"]))),
        "tipo_creatura": d["type"], "taglia": d["size"],
        "allineamento": d["align"],
        "azioni_nomi_da_completare": list(d["actions"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_rejection")
    token=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    summary=(
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    return {
        "id":"ref_"+hashlib.sha256(token.encode()).hexdigest()[:32],
        "name": name, "physical_page": d["page"],
        "source_excerpt": summary,
        "source_text_checksum": hashlib.sha256(summary.encode()).hexdigest(),
        "attributes":deepcopy(attrs),"status":"source_core_only","writes":0,
    }
