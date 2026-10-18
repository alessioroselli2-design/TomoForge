"""Original-source proof for six Italian Monster Manual dinosaur statblocks.

Two physical PDF pages 79–80 show six distinct boxed statblocks. Independently
visually read from 353-page user licensed scan, SHA256 matches active catalog.
Only concise core stats are stored in repository, no source PDF/pages.
Module returns eligibility only; ZERO database writes.
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
PAGE_COUNT = 353
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")
MONSTERS: dict[str, dict[str, Any]] = {
    "Allosauro": {
        "page": 79,
        "kind": "Bestia Grande",
        "type": "Bestia",
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "13 (armatura naturale)",
        "hp": "51 (6d10 + 18)",
        "speed": "18 m",
        "gs": "2",
        "abilities": {
            "for": "19",
            "des": "13",
            "cos": "17",
            "int": "2",
            "sag": "12",
            "car": "5"
        },
        "id": "ref_de46ee61ca6db0d6a6baeac61f75cca3",
        "digest": "ec6c1774826fb7f46c14eac3ff7b836fc2b4685fe709e83aca4c83faa03abb12"
    },
    "Anchilosauro": {
        "page": 79,
        "kind": "Bestia Enorme",
        "type": "Bestia",
        "size": "Enorme",
        "align": "senza allineamento",
        "ac": "15 (armatura naturale)",
        "hp": "68 (8d12 + 16)",
        "speed": "9 m",
        "gs": "3",
        "abilities": {
            "for": "19",
            "des": "11",
            "cos": "15",
            "int": "2",
            "sag": "12",
            "car": "5"
        },
        "id": "ref_f3b214adc9da52b9c5e826d3000a03a7",
        "digest": "9df99ca969fc39422cc69dc211a3f2d51733bcbe86a608fe24053d55e816a1fa"
    },
    "Plesiosauro": {
        "page": 80,
        "kind": "Bestia Grande",
        "type": "Bestia",
        "size": "Grande",
        "align": "senza allineamento",
        "ac": "13 (armatura naturale)",
        "hp": "68 (8d10 + 24)",
        "speed": "6 m, nuotare 12 m",
        "gs": "2",
        "abilities": {
            "for": "18",
            "des": "15",
            "cos": "16",
            "int": "2",
            "sag": "12",
            "car": "5"
        },
        "id": "ref_571ec79e60b133c59c278e6048189914",
        "digest": "d87dac69fe4009235f0cb9c129d0ca4b1248f3d4f1018d95c1d08891cafc1361"
    },
    "Pteranodonte": {
        "page": 80,
        "kind": "Bestia Media",
        "type": "Bestia",
        "size": "Media",
        "align": "senza allineamento",
        "ac": "13 (armatura naturale)",
        "hp": "13 (3d8)",
        "speed": "3 m, volare 18 m",
        "gs": "1/4",
        "abilities": {
            "for": "12",
            "des": "15",
            "cos": "10",
            "int": "2",
            "sag": "9",
            "car": "5"
        },
        "id": "ref_0a71f5b3b6b83fad08f6afb73b216ef0",
        "digest": "2bac44ce8f8ec3bba1773f54c2fd548314421a855e31bbba40eecf8dcf0bb1d4"
    },
    "Tirannosauro": {
        "page": 80,
        "kind": "Bestia Enorme",
        "type": "Bestia",
        "size": "Enorme",
        "align": "senza allineamento",
        "ac": "13 (armatura naturale)",
        "hp": "136 (13d12 + 52)",
        "speed": "15 m",
        "gs": "8",
        "abilities": {
            "for": "25",
            "des": "10",
            "cos": "19",
            "int": "2",
            "sag": "12",
            "car": "9"
        },
        "id": "ref_e42d4ea5dc0ffa98ddbaab7f762e4501",
        "digest": "22aceed47e8181f8147f4f7d620f6d2155f8327030522a2c86070586e48427c8"
    },
    "Triceratopo": {
        "page": 80,
        "kind": "Bestia Enorme",
        "type": "Bestia",
        "size": "Enorme",
        "align": "senza allineamento",
        "ac": "13 (armatura naturale)",
        "hp": "95 (10d12 + 30)",
        "speed": "15 m",
        "gs": "5",
        "abilities": {
            "for": "22",
            "des": "9",
            "cos": "17",
            "int": "2",
            "sag": "11",
            "car": "5"
        },
        "id": "ref_cceb0f904498f31335cc79f04194aa9e",
        "digest": "a00aacb40f666b3d73aa971a00ebc861d26245a6c558666108e9c255aba33483"
    }
}

def excerpt(name: str, d: dict[str, Any]) -> str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )

def audit(name: str, catalog: dict[str, Any] | None,
          id_exists: bool = False,
          monster_name_matches: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unknown_named_dinosaur_statblock")
    if id_exists or monster_name_matches:
        raise ValueError("already_existing_monster")
    expected = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILENAME,
        "physical_sha256": SHA256, "physical_pages": PAGE_COUNT,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in expected.items()):
        raise ValueError("registered_authority_mismatch")
    d = MONSTERS[name]
    if d["page"] not in (79, 80):
        raise ValueError("wrong_physical_page")
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    generated = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if generated != d["id"]:
        raise ValueError("source_record_identity_changed")
    if d["kind"] != f"{d['type']} {d['size']}":
        raise ValueError("source_category_changed")
    summary = excerpt(name, d)
    checksum = hashlib.sha256(summary.encode("utf-8")).hexdigest()
    if checksum != d["digest"]:
        raise ValueError("sealed_original_numbers_changed")
    attrs = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "caratteristiche": d["abilities"], "tipo_creatura": d["type"],
        "taglia": d["size"], "allineamento": d["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("numeric_or_identity_gate")
    hp = HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("wrong_hit_dice_expression")
    average, dice, faces, bonus = hp.groups()
    if int(average) != int(dice) * (int(faces)+1) // 2 + int(bonus or 0):
        raise ValueError("hit_dice_average_does_not_match")
    if set(d["abilities"]) != {"for","des","cos","int","sag","car"} or any(
        not str(v).isdigit() or not 1 <= int(v) <= 30 for v in d["abilities"].values()
    ):
        raise ValueError("ability_score_gate")
    return {
        "id": generated,"name": name,"physical_page": d["page"],
        "source_excerpt": summary,"source_text_checksum": checksum,
        "attributes": deepcopy(attrs),"writes": 0,
    }
