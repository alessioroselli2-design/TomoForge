"""Original source proof, four independently named Red Dragons MM p97–98.

Owner's 353-page Italian licensed scan was directly visually inspected and
whole-file SHA256 matched the active Supabase authority. Physical p98
contains three independent boxed statblocks. This module is READ ONLY and
must not be used to bypass blocked DB connector mutation.
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
    "Drago Rosso Antico": {
        "page": 97,
        "kind": "Drago Mastodontico",
        "type": "Drago",
        "size": "Mastodontico",
        "align": "caotico malvagio",
        "ac": "22 (armatura naturale)",
        "hp": "546 (28d20 + 252)",
        "speed": "12 m, scalare 12 m, volare 24 m",
        "gs": "24",
        "abilities": {
            "for": "30",
            "des": "10",
            "cos": "29",
            "int": "18",
            "sag": "15",
            "car": "23"
        },
        "id": "ref_1a361d1de24a6a999fa384eb9fcdea70",
        "digest": "6cf59a77f1d0594d883a60d465872173269d0c5bf15a4012dcd0c6fdebe9701d"
    },
    "Drago Rosso Adulto": {
        "page": 98,
        "kind": "Drago Enorme",
        "type": "Drago",
        "size": "Enorme",
        "align": "caotico malvagio",
        "ac": "19 (armatura naturale)",
        "hp": "256 (19d12 + 133)",
        "speed": "12 m, scalare 12 m, volare 24 m",
        "gs": "17",
        "abilities": {
            "for": "27",
            "des": "10",
            "cos": "25",
            "int": "16",
            "sag": "13",
            "car": "21"
        },
        "id": "ref_30a38ff2fe466f72ad8e08fb84574313",
        "digest": "ff4e33558dfc282e39fee5a3e629dd3601c12f4aedc7b8fbc0068d164b988f98"
    },
    "Drago Rosso Giovane": {
        "page": 98,
        "kind": "Drago Grande",
        "type": "Drago",
        "size": "Grande",
        "align": "caotico malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "178 (17d10 + 85)",
        "speed": "12 m, scalare 12 m, volare 24 m",
        "gs": "10",
        "abilities": {
            "for": "23",
            "des": "10",
            "cos": "21",
            "int": "14",
            "sag": "11",
            "car": "19"
        },
        "id": "ref_e76b6afcecf8e3aa7cca4eb21c128349",
        "digest": "38f9fc7af347d5a71dcf121a4e53e7434128cf2d840a04f858b5f3439a442c6d"
    },
    "Drago Rosso Cucciolo": {
        "page": 98,
        "kind": "Drago Medio",
        "type": "Drago",
        "size": "Medio",
        "align": "caotico malvagio",
        "ac": "17 (armatura naturale)",
        "hp": "75 (10d8 + 30)",
        "speed": "9 m, scalare 9 m, volare 18 m",
        "gs": "4",
        "abilities": {
            "for": "19",
            "des": "10",
            "cos": "17",
            "int": "12",
            "sag": "11",
            "car": "15"
        },
        "id": "ref_44c1e5c28079f98903d268dccbb583fa",
        "digest": "e54dbce78ea5a87f25de40b8607adff7cbe67622f309c23daadc91acd3a581e1"
    }
}

def source_excerpt(name:str,d:dict[str,Any])->str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )

def audit(name:str,catalog:dict[str,Any]|None,
          id_found:bool=False, other_monster_names:list[dict[str,Any]]|None=None)->dict[str,Any]:
    if name not in MONSTERS:
        raise ValueError("unknown_red_dragon_statblock")
    if id_found or other_monster_names:
        raise ValueError("already_present_monster")
    correct={
        "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
        "physical_sha256":SHA256,"physical_pages":PAGES,
        "source_role":"authority","source_status":"active",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in correct.items()):
        raise ValueError("source_authority_mismatch")
    d=MONSTERS[name]
    if d["page"] not in (97,98) or d["kind"]!=f"{d['type']} {d['size']}":
        raise ValueError("page_or_category_mismatch")
    ident="ref_"+hashlib.sha256(
        f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}".encode()
    ).hexdigest()[:32]
    if ident!=d["id"]:
        raise ValueError("identity_sha_mismatch")
    excerpt=source_excerpt(name,d)
    digest=hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    if digest!=d["digest"]:
        raise ValueError("original_source_numbers_modified")
    attrs={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],
        "velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":d["abilities"],"tipo_creatura":d["type"],
        "taglia":d["size"],"allineamento":d["align"],
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("source_semantic_gate")
    parsed=HP.fullmatch(d["hp"])
    if not parsed:
        raise ValueError("invalid_hp_dice")
    avg,n,faces,mod=map(int,parsed.groups())
    if avg!=n*(faces+1)//2+mod:
        raise ValueError("incorrect_hp_mean")
    if set(d["abilities"])!={"for","des","cos","int","sag","car"} or any(
        not 1<=int(v)<=30 for v in d["abilities"].values()
    ):
        raise ValueError("missing_ability_scores")
    return {"id":ident,"name":name,"physical_page":d["page"],
            "source_excerpt":excerpt,"source_text_checksum":digest,
            "attributes":deepcopy(attrs),"writes":0}
