"""Original Italian MM p81,82,84,85 independent boxed monster-source audits.

Original user-licensed 353-page scanned Monster Manual physical PDF pages
inspected directly, full-file SHA-256 equals registered catalog authority.
Physical p83 Dracolich archetype prose is NOT an independent creature;
p84 adult blue dracolich and p85 young red shadow dragon ARE independent
printed monster blocks. Existing Eberron Doppelganger 'ability' is not a
monster duplicate; verify same-type identity before DB writes. Read-only.
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
DICE=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+) [+] ([0-9]+)[)]$")
MONSTERS: dict[str, dict[str, Any]] = {
    "Divoracervelli": {
        "page": 81,
        "kind": "Aberrazione Minuscola",
        "type": "Aberrazione",
        "size": "Minuscola",
        "align": "legale malvagio",
        "ac": "12",
        "hp": "21 (6d4 + 6)",
        "speed": "12 m",
        "gs": "2",
        "abilities": {
            "for": "6",
            "des": "14",
            "cos": "13",
            "int": "12",
            "sag": "11",
            "car": "10"
        },
        "id": "ref_eb32a97f5d258ca2a633e7b189a778d0",
        "digest": "fcc683db852a92b7461d52d2cbbf4f7a3f0d935352f5baea7dab2c0bea50b598"
    },
    "Doppelganger": {
        "page": 82,
        "kind": "Mostruosità Media (mutaforma)",
        "type": "Mostruosità",
        "size": "Media",
        "align": "neutrale",
        "ac": "14",
        "hp": "52 (8d8 + 16)",
        "speed": "9 m",
        "gs": "3",
        "abilities": {
            "for": "11",
            "des": "18",
            "cos": "14",
            "int": "11",
            "sag": "12",
            "car": "14"
        },
        "id": "ref_7bbecaa532317dfef2f611aa0e9d44e4",
        "digest": "48bb7ca74482b565d7a4d8dcb1caca84438b285784bd413418e465b05705c4fe"
    },
    "Dracolich Blu Adulto": {
        "page": 84,
        "kind": "Non morto Enorme",
        "type": "Non morto",
        "size": "Enorme",
        "align": "legale malvagio",
        "ac": "19 (armatura naturale)",
        "hp": "225 (18d12 + 108)",
        "speed": "12 m, scavare 9 m, volare 24 m",
        "gs": "17",
        "abilities": {
            "for": "25",
            "des": "10",
            "cos": "23",
            "int": "16",
            "sag": "15",
            "car": "19"
        },
        "id": "ref_c5a5a19e8340044a349023c159ea6e5d",
        "digest": "0055eb83cbf8c9784fa3dff8516f1a25e28d4fd80d4c96775747526508aee37d"
    },
    "Drago D’Ombra Rosso Giovane": {
        "page": 85,
        "kind": "Drago Grande",
        "type": "Drago",
        "size": "Grande",
        "align": "caotico malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "178 (17d10 + 85)",
        "speed": "12 m, scalare 12 m, volare 24 m",
        "gs": "13",
        "abilities": {
            "for": "23",
            "des": "10",
            "cos": "21",
            "int": "14",
            "sag": "11",
            "car": "19"
        },
        "id": "ref_6e95eac2c3ec76dc265976229452d030",
        "digest": "a93b45c6fd24cf90fab799d639755225bae95b4e561c3ca98e00005efa63346a"
    }
}

def excerpt(name: str, d: dict[str,Any]) -> str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )

def audit(name: str, catalog: dict[str,Any] | None,
          existing_id: bool=False, existing_monster_names: list[dict[str,Any]] | None=None) -> dict[str,Any]:
    if name not in MONSTERS:
        raise ValueError("not_a_sealed_independent_statblock")
    if existing_id or existing_monster_names:
        raise ValueError("duplicate_existing_monster")
    required={
        "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
        "physical_sha256":SHA256,"physical_pages":PAGE_COUNT,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in required.items()):
        raise ValueError("source_authority_drift")
    d=MONSTERS[name]
    if d["page"] not in (81,82,84,85):
        raise ValueError("physical_source_page_mismatch")
    if not d["kind"].startswith(d["type"]) or f" {d['size']}" not in d["kind"]:
        raise ValueError("type_or_size_mismatch")
    token=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    record_id="ref_"+hashlib.sha256(token.encode()).hexdigest()[:32]
    if record_id!=d["id"]:
        raise ValueError("identity_fingerprint_mismatch")
    core=excerpt(name,d)
    digest=hashlib.sha256(core.encode("utf-8")).hexdigest()
    if digest!=d["digest"]:
        raise ValueError("original_source_core_changed")
    attrs={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],
        "velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":d["abilities"],"tipo_creatura":d["type"],
        "taglia":d["size"],"allineamento":d["align"],
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("statblock_numeric_gate")
    match=DICE.fullmatch(d["hp"])
    if match is None:
        raise ValueError("invalid_hit_dice_expression")
    avg,count,faces,bonus=map(int,match.groups())
    if avg!=count*(faces+1)//2+bonus:
        raise ValueError("hit_dice_mean_mismatch")
    if set(d["abilities"])!={"for","des","cos","int","sag","car"} or any(
        not 1<=int(v)<=30 for v in d["abilities"].values()
    ):
        raise ValueError("six_abilities_incomplete")
    return {
        "id":record_id,"name":name,"physical_page":d["page"],
        "source_excerpt":core,"source_text_checksum":digest,
        "attributes":deepcopy(attrs),"writes":0,
    }
