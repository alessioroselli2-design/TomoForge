"""Four independent blue dragon original Italian Monster Manual statblocks.

Physical p91–92 of owner's licensed 353-page scan independently inspected,
whole-file SHA-256 verified. p92 has THREE named boxed statblocks. p93 is
dragon lore and lair information, not an independent statblock. Core fields
only, no PDF copying and no DB writes.
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
HP=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+) [+] ([0-9]+)[)]$")
MONSTERS: dict[str, dict[str, Any]] = {
    "Drago Blu Antico": {
        "page": 91,
        "kind": "Drago Mastodontico",
        "type": "Drago",
        "size": "Mastodontico",
        "align": "legale malvagio",
        "ac": "22 (armatura naturale)",
        "hp": "481 (26d20 + 208)",
        "speed": "12 m, scavare 12 m, volare 24 m",
        "gs": "23",
        "abilities": {
            "for": "29",
            "des": "10",
            "cos": "27",
            "int": "18",
            "sag": "17",
            "car": "21"
        },
        "id": "ref_7a7cd207a285b877255b7785c1ac3e4f",
        "digest": "6a902ba12bd5240acc4cf7569d7c386ee3b0f8d51c570b10ec73c9632358a895"
    },
    "Drago Blu Adulto": {
        "page": 92,
        "kind": "Drago Enorme",
        "type": "Drago",
        "size": "Enorme",
        "align": "legale malvagio",
        "ac": "19 (armatura naturale)",
        "hp": "225 (18d12 + 108)",
        "speed": "12 m, scavare 9 m, volare 24 m",
        "gs": "16",
        "abilities": {
            "for": "25",
            "des": "10",
            "cos": "23",
            "int": "16",
            "sag": "15",
            "car": "19"
        },
        "id": "ref_4f5b1db42fabac1450f4273c1bbbf8e9",
        "digest": "739058e1c8cae44465a333dc895c81c12035714fbd260636c483ef25d0f5781c"
    },
    "Drago Blu Giovane": {
        "page": 92,
        "kind": "Drago Grande",
        "type": "Drago",
        "size": "Grande",
        "align": "legale malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "152 (16d10 + 64)",
        "speed": "12 m, scavare 6 m, volare 24 m",
        "gs": "9",
        "abilities": {
            "for": "21",
            "des": "10",
            "cos": "19",
            "int": "14",
            "sag": "13",
            "car": "17"
        },
        "id": "ref_93239a0c30a18fc8225ec45c9be85c84",
        "digest": "4ac5e6cea89a03b80da60849b20cb21f269d9c9ead614becb9a36f81eb58757f"
    },
    "Drago Blu Cucciolo": {
        "page": 92,
        "kind": "Drago Medio",
        "type": "Drago",
        "size": "Medio",
        "align": "legale malvagio",
        "ac": "17 (armatura naturale)",
        "hp": "52 (8d8 + 16)",
        "speed": "9 m, scavare 4,5 m, volare 18 m",
        "gs": "3",
        "abilities": {
            "for": "17",
            "des": "10",
            "cos": "15",
            "int": "12",
            "sag": "11",
            "car": "15"
        },
        "id": "ref_5ab253f7eb833459653eb015195749cc",
        "digest": "ff103428129311566c2100fc1c3d0438d64c48bec754ad07db5738da4fbbe1de"
    }
}

def source_excerpt(name: str,d:dict[str,Any])->str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )

def audit(name: str,catalog:dict[str,Any]|None,
          id_exists:bool=False, duplicate_monsters:list[dict[str,Any]]|None=None)->dict[str,Any]:
    if name not in MONSTERS:
        raise ValueError("unknown_printed_blue_dragon")
    if id_exists or duplicate_monsters:
        raise ValueError("existing_monster_duplicate")
    required={
        "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
        "physical_sha256":SHA256,"physical_pages":PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in required.items()):
        raise ValueError("original_registered_source_drift")
    d=MONSTERS[name]
    if d["page"] not in (91,92):
        raise ValueError("source_page_out_of_scope")
    if d["kind"]!=f"{d['type']} {d['size']}":
        raise ValueError("type_or_size_drift")
    sid="ref_"+hashlib.sha256(f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}".encode()).hexdigest()[:32]
    if sid!=d["id"]:
        raise ValueError("identity_sha_changed")
    excerpt=source_excerpt(name,d)
    checksum=hashlib.sha256(excerpt.encode()).hexdigest()
    if checksum!=d["digest"]:
        raise ValueError("source_core_statblock_drift")
    attrs={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],
        "velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":d["abilities"],"tipo_creatura":d["type"],
        "taglia":d["size"],"allineamento":d["align"],
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate_failed")
    match=HP.fullmatch(d["hp"])
    if match is None:
        raise ValueError("invalid_original_hp")
    avg,n,die,bonus=map(int,match.groups())
    if avg!=n*(die+1)//2+bonus:
        raise ValueError("hp_average_mismatch")
    if set(d["abilities"])!={"for","des","cos","int","sag","car"} or any(
        not 1<=int(v)<=30 for v in d["abilities"].values()
    ):
        raise ValueError("missing_abilities")
    return {"id":sid,"name":name,"physical_page":d["page"],
            "source_excerpt":excerpt,"source_text_checksum":checksum,
            "attributes":deepcopy(attrs),"writes":0}
