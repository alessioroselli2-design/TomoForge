"""Source-locked eligibility for Italian MM devil statblocks on p75–78.

The original private 353-page Italian scanned PDF was opened visually, including
high-resolution crops of each statblock. Whole-file SHA256 independently
matches active Supabase registered licensed authority. Both p76 blocks are
separate monster identities. The p78 Imp matches an existing PHB verified
monster and must NOT be duplicated. This audit makes ZERO DB writes.
"""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import (
    monster_identity_sanity_flags,
    monster_semantic_numeric_flags,
)

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGE_COUNT = 353
IMPORTED_IMP_ID = "ref_6e1a9996179d5a93a027a31bc30b5d2f"
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")
MONSTERS: dict[str, dict[str, Any]] = {
    "Diavolo Delle Catene": {
        "page": 75,
        "kind": "Immondo Medio (diavolo)",
        "type": "Immondo",
        "size": "Medio",
        "align": "legale malvagio",
        "ac": "16 (armatura naturale)",
        "hp": "85 (10d8 + 40)",
        "speed": "9 m",
        "gs": "8",
        "abilities": {
            "for": "18",
            "des": "15",
            "cos": "18",
            "int": "11",
            "sag": "12",
            "car": "14"
        },
        "id": "ref_8aec914fae394add37b212eb2034c722",
        "digest": "4b0e31e6694c7acdfd0e8efa5cd1d05598ec76c2df6f27204fa843f2fd568c9b"
    },
    "Diavolo Spinato": {
        "page": 76,
        "kind": "Immondo Piccolo (diavolo)",
        "type": "Immondo",
        "size": "Piccolo",
        "align": "legale malvagio",
        "ac": "13 (armatura naturale)",
        "hp": "22 (5d6 + 5)",
        "speed": "6 m, volare 12 m",
        "gs": "2",
        "abilities": {
            "for": "10",
            "des": "15",
            "cos": "12",
            "int": "11",
            "sag": "14",
            "car": "8"
        },
        "id": "ref_86611030aeb151ac26373bb8b8ed0561",
        "digest": "bf5bb01a4d6159fd3ecefeae55516e277b25d97bf073b2bb675f582b3727b14e"
    },
    "Diavolo Uncinato": {
        "page": 76,
        "kind": "Immondo Medio (diavolo)",
        "type": "Immondo",
        "size": "Medio",
        "align": "legale malvagio",
        "ac": "15 (armatura naturale)",
        "hp": "110 (13d8 + 52)",
        "speed": "9 m",
        "gs": "5",
        "abilities": {
            "for": "16",
            "des": "17",
            "cos": "18",
            "int": "12",
            "sag": "14",
            "car": "14"
        },
        "id": "ref_220b24f12fd13e33eeaeee4de1c84f2c",
        "digest": "110a3964fb9d711998cb57044f978946d51e8097f023bf09dd3b3b74177d0085"
    },
    "Erinni": {
        "page": 77,
        "kind": "Immondo Medio (diavolo)",
        "type": "Immondo",
        "size": "Medio",
        "align": "legale malvagio",
        "ac": "18 (armatura completa)",
        "hp": "153 (18d8 + 72)",
        "speed": "9 m, volare 18 m",
        "gs": "12",
        "abilities": {
            "for": "18",
            "des": "16",
            "cos": "18",
            "int": "14",
            "sag": "14",
            "car": "18"
        },
        "id": "ref_536a1f63be1d08b6dcb7d8f7a833aa18",
        "digest": "479a867ab15189f3b3bcd20a6bf0a8fd00276a40aa3354c88c89efeab3ca56ef"
    },
    "Lemure": {
        "page": 78,
        "kind": "Immondo Medio (diavolo)",
        "type": "Immondo",
        "size": "Medio",
        "align": "legale malvagio",
        "ac": "7",
        "hp": "13 (3d8)",
        "speed": "4,5 m",
        "gs": "0",
        "abilities": {
            "for": "10",
            "des": "5",
            "cos": "11",
            "int": "1",
            "sag": "11",
            "car": "3"
        },
        "id": "ref_63d1d252594db9e408e2daa42027d399",
        "digest": "6feaff5ed68e3479adc4ad981e696e1bfcc802926ae80c8625140fc17c566082"
    }
}

def source_excerpt(name: str, d: dict[str, Any]) -> str:
    return (
        f"{name}. {d['kind']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )

def audit(name: str, source: dict[str, Any] | None,
          found_by_id: bool = False,
          duplicate_monsters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if name == "Imp":
        raise ValueError("already_verified_phb_imp_no_duplicate")
    if name not in MONSTERS:
        raise ValueError("unverified_or_missing_source_statblock")
    if found_by_id or duplicate_monsters:
        raise ValueError("monster_collision")
    expected_source = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGE_COUNT,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(source, dict) or any(
        source.get(k) != v for k, v in expected_source.items()
    ):
        raise ValueError("registered_source_mismatch")
    d = MONSTERS[name]
    if d["page"] not in (75, 76, 77, 78):
        raise ValueError("physical_page_drift")
    identity = "ref_" + hashlib.sha256(
        f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}".encode()
    ).hexdigest()[:32]
    if identity != d["id"]:
        raise ValueError("source_identity_mismatch")
    summary = source_excerpt(name, d)
    digest = hashlib.sha256(summary.encode("utf-8")).hexdigest()
    if digest != d["digest"]:
        raise ValueError("statblock_source_fields_modified")
    if not d["kind"].startswith(d["type"]) or f" {d['size']}" not in d["kind"]:
        raise ValueError("statblock_source_fields_modified")
    attrs = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "caratteristiche": d["abilities"], "tipo_creatura": d["type"],
        "taglia": d["size"], "allineamento": d["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("identity_or_numeric_validation_failed")
    match = HP_RE.fullmatch(d["hp"])
    if match is None:
        raise ValueError("invalid_hit_dice_expression")
    average, dice, faces, bonus = match.groups()
    if int(average) != int(dice) * (int(faces) + 1) // 2 + int(bonus or 0):
        raise ValueError("hit_dice_average_mismatch")
    if set(d["abilities"]) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not str(v).isdigit() or not 1 <= int(v) <= 30
        for v in d["abilities"].values()
    ):
        raise ValueError("six_ability_scores_invalid")
    return {
        "id": identity, "name": name, "physical_page": d["page"],
        "source_excerpt": summary, "source_text_checksum": digest,
        "attributes": deepcopy(attrs),
        "status": "eligible_original_source_core_stats_only", "writes": 0,
    }
