"""Original private Italian Monster Manual source-proofed black dragons p94–95.

The scanned licensed 353-page PDF source SHA matches active registry.
p94 contains Black Ancient dragon, p95 has Adult, Young and Wyrmling.
Each printed named statblock independently checked, without copying
licensed pages to GitHub. ZERO database writes.
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
HP=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+) [+] ([0-9]+)[)]$")
MONSTERS: dict[str, dict[str, Any]] = {
    "Drago Nero Antico": {
        "page": 94,
        "kind": "Drago Mastodontico",
        "type": "Drago",
        "size": "Mastodontico",
        "align": "caotico malvagio",
        "ac": "22 (armatura naturale)",
        "hp": "367 (21d20 + 147)",
        "speed": "12 m, nuotare 12 m, volare 24 m",
        "gs": "21",
        "abilities": {
            "for": "27",
            "des": "14",
            "cos": "25",
            "int": "16",
            "sag": "15",
            "car": "19"
        },
        "id": "ref_3c5ba98a1e61e740ed11edd58997d71b",
        "digest": "124683eae05b33e30cec1194edfe09a4da1adfb1054238d72489a26fd71061ea"
    },
    "Drago Nero Adulto": {
        "page": 95,
        "kind": "Drago Enorme",
        "type": "Drago",
        "size": "Enorme",
        "align": "caotico malvagio",
        "ac": "19 (armatura naturale)",
        "hp": "195 (17d12 + 85)",
        "speed": "12 m, nuotare 12 m, volare 24 m",
        "gs": "14",
        "abilities": {
            "for": "23",
            "des": "14",
            "cos": "21",
            "int": "14",
            "sag": "13",
            "car": "17"
        },
        "id": "ref_3ff56089ed5da32a4e277f1a821eac53",
        "digest": "393357366eb60eb06c39a9f1c9c8251e73f51246f3d07845f4207024b9b4c41c"
    },
    "Drago Nero Giovane": {
        "page": 95,
        "kind": "Drago Grande",
        "type": "Drago",
        "size": "Grande",
        "align": "caotico malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "127 (15d10 + 45)",
        "speed": "12 m, nuotare 12 m, volare 24 m",
        "gs": "7",
        "abilities": {
            "for": "19",
            "des": "14",
            "cos": "17",
            "int": "12",
            "sag": "11",
            "car": "15"
        },
        "id": "ref_8344efdc0a64a51de3fb53372da80160",
        "digest": "3a3486b1406eed5f78aa1585524ba3c576a14422a8d27b7f335e20703f177d03"
    },
    "Drago Nero Cucciolo": {
        "page": 95,
        "kind": "Drago Medio",
        "type": "Drago",
        "size": "Medio",
        "align": "caotico malvagio",
        "ac": "17 (armatura naturale)",
        "hp": "33 (6d8 + 6)",
        "speed": "9 m, nuotare 9 m, volare 18 m",
        "gs": "2",
        "abilities": {
            "for": "15",
            "des": "14",
            "cos": "13",
            "int": "10",
            "sag": "11",
            "car": "13"
        },
        "id": "ref_8c0fd4c24496d22ee32639f444e5b563",
        "digest": "e16ad14b9d1fbf07688227e27ec27401b1b13a0922ab7c84069a31fccfa1215d"
    }
}

def source_excerpt(name: str,d:dict[str,Any])->str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )

def audit(name: str, source:dict[str,Any]|None,
          existing_id:bool=False, duplicate_monsters:list[dict[str,Any]]|None=None)->dict[str,Any]:
    if name not in MONSTERS:
        raise ValueError("original_black_dragon_not_found")
    if existing_id or duplicate_monsters:
        raise ValueError("existing_monster_collision")
    required={
        "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
        "physical_sha256":SHA256,"physical_pages":PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(source,dict) or any(source.get(k)!=v for k,v in required.items()):
        raise ValueError("original_source_mismatch")
    d=MONSTERS[name]
    if d["page"] not in (94,95):
        raise ValueError("page_not_sealed")
    if d["kind"]!=f"{d['type']} {d['size']}":
        raise ValueError("type_or_size_disagrees")
    token=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    sid="ref_"+hashlib.sha256(token.encode()).hexdigest()[:32]
    if sid!=d["id"]:
        raise ValueError("identity_hash_disagrees")
    excerpt=source_excerpt(name,d)
    digest=hashlib.sha256(excerpt.encode()).hexdigest()
    if digest!=d["digest"]:
        raise ValueError("original_printed_numbers_changed")
    attrs={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],
        "velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":d["abilities"],"tipo_creatura":d["type"],
        "taglia":d["size"],"allineamento":d["align"],
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate_failed")
    parsed=HP.fullmatch(d["hp"])
    if parsed is None:
        raise ValueError("invalid_original_pf_dice")
    avg,num,die,bonus=map(int,parsed.groups())
    if avg!=num*(die+1)//2+bonus:
        raise ValueError("incorrect_pf_average")
    if set(d["abilities"])!={"for","des","cos","int","sag","car"} or any(
        not 1<=int(v)<=30 for v in d["abilities"].values()
    ):
        raise ValueError("six_abilities_incomplete")
    return {"id":sid,"name":name,"physical_page":d["page"],
            "source_excerpt":excerpt,"source_text_checksum":digest,
            "attributes":deepcopy(attrs),"writes":0}
