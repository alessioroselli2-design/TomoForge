"""Four independently named white dragon statblocks from original Italian MM.

The owner's licensed 353-page Italian scan was visually inspected at physical
PDF pages 87–89, file SHA-256 compared with registered licensed authority.
Page 86 general dragon lore is NOT an independent creature; physical p88 has
two separate statblocks. Source-gated concise core fields only. No DB writes.
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
    "Drago Bianco Antico": {
        "page": 87,
        "kind": "Drago Mastodontico",
        "type": "Drago",
        "size": "Mastodontico",
        "align": "caotico malvagio",
        "ac": "20 (armatura naturale)",
        "hp": "333 (18d20 + 144)",
        "speed": "12 m, nuotare 12 m, scavare 12 m, volare 24 m",
        "gs": "20",
        "abilities": {
            "for": "26",
            "des": "10",
            "cos": "26",
            "int": "10",
            "sag": "13",
            "car": "14"
        },
        "id": "ref_6779e2c72381e577fb0929693464cfd8",
        "digest": "4c1d6e1ad3ab0213504aa249d50863adc3d13be30c56dc06eb9599c53663d10c"
    },
    "Drago Bianco Adulto": {
        "page": 88,
        "kind": "Drago Enorme",
        "type": "Drago",
        "size": "Enorme",
        "align": "caotico malvagio",
        "ac": "18 (armatura naturale)",
        "hp": "200 (16d12 + 96)",
        "speed": "12 m, nuotare 12 m, scavare 9 m, volare 24 m",
        "gs": "13",
        "abilities": {
            "for": "22",
            "des": "10",
            "cos": "22",
            "int": "8",
            "sag": "12",
            "car": "12"
        },
        "id": "ref_e8871e1ce8d86943a6614daff17025b8",
        "digest": "a1efcafd7083f11d3e5c68df885bc880e2e9b9d8805344eb30902a4ae015b1ae"
    },
    "Drago Bianco Giovane": {
        "page": 88,
        "kind": "Drago Grande",
        "type": "Drago",
        "size": "Grande",
        "align": "caotico malvagio",
        "ac": "17 (armatura naturale)",
        "hp": "133 (14d10 + 56)",
        "speed": "12 m, nuotare 12 m, scavare 6 m, volare 24 m",
        "gs": "6",
        "abilities": {
            "for": "18",
            "des": "10",
            "cos": "18",
            "int": "6",
            "sag": "11",
            "car": "12"
        },
        "id": "ref_ceb4986c3abcfd3e7400ad593cb2b730",
        "digest": "e9190bcabd0dc7d1c1af19defed8c54a84b3e03f542828b8613ceeee0e1ac561"
    },
    "Drago Bianco Cucciolo": {
        "page": 89,
        "kind": "Drago Medio",
        "type": "Drago",
        "size": "Medio",
        "align": "caotico malvagio",
        "ac": "16 (armatura naturale)",
        "hp": "32 (5d8 + 10)",
        "speed": "9 m, nuotare 9 m, scavare 4,5 m, volare 18 m",
        "gs": "2",
        "abilities": {
            "for": "14",
            "des": "10",
            "cos": "14",
            "int": "5",
            "sag": "10",
            "car": "11"
        },
        "id": "ref_1b21909f535eb5460186df2a87f7eb69",
        "digest": "56c2785cc30c1ea7290ac2e32980f44802b0b9ae5ed34c062f279f61d34cc4d5"
    }
}

def original_excerpt(name: str,d: dict[str,Any]) -> str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )

def audit(name: str,catalog: dict[str,Any] | None,
          duplicate_id: bool=False,
          duplicate_monsters: list[dict[str,Any]] | None=None) -> dict[str,Any]:
    if name not in MONSTERS:
        raise ValueError("no_named_original_dragon_statblock")
    if duplicate_id or duplicate_monsters:
        raise ValueError("dragon_already_exists")
    expected={
        "logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
        "physical_sha256":SHA256,"physical_pages":PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("unverified_registered_authority")
    d=MONSTERS[name]
    if d["page"] not in (87,88,89):
        raise ValueError("page_not_from_original_batch")
    if d["kind"]!=f"{d['type']} {d['size']}":
        raise ValueError("original_dragon_type_size_changed")
    token=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    expected_id="ref_"+hashlib.sha256(token.encode()).hexdigest()[:32]
    if expected_id!=d["id"]:
        raise ValueError("deterministic_source_id_changed")
    source=original_excerpt(name,d)
    digest=hashlib.sha256(source.encode()).hexdigest()
    if digest!=d["digest"]:
        raise ValueError("source_core_fingerprint_changed")
    attrs={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],
        "velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":d["abilities"],"tipo_creatura":d["type"],
        "taglia":d["size"],"allineamento":d["align"],
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_core_statblock_gate")
    parsed=HP.fullmatch(d["hp"])
    if not parsed:
        raise ValueError("bad_original_hit_dice")
    avg,n,die,bonus=map(int,parsed.groups())
    if avg!=n*(die+1)//2+bonus:
        raise ValueError("incoherent_original_hit_points")
    if set(d["abilities"])!={"for","des","cos","int","sag","car"} or any(
        not 1<=int(v)<=30 for v in d["abilities"].values()
    ):
        raise ValueError("six_ability_scores_invalid")
    return {
        "id":expected_id,"name":name,"physical_page":d["page"],
        "source_excerpt":source,"source_text_checksum":digest,
        "attributes":deepcopy(attrs),"writes":0,
    }
