"""Original-source core statblock audit — Draghi d’Ottone.

Licensed user-provided Italian Monster Manual (353 physical PDF pages);
high-resolution source pages manually inspected. Only condensed core fields
are stored: full abilities, actions, spells and legendary/lair entries are
not certified here. This audit never writes to the database.
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
_RAW_SPECS: dict[str,list[Any]] = {
    "Drago D’Ottone Antico": [
        115,
        "Mastodontico",
        "caotico buono",
        "20 (armatura naturale)",
        "297 (17d20 + 119)",
        "12 m, scavare 12 m, volare 24 m",
        "20",
        [
            27,
            10,
            25,
            16,
            15,
            19
        ]
    ],
    "Drago D’Ottone Adulto": [
        116,
        "Enorme",
        "caotico buono",
        "18 (armatura naturale)",
        "172 (15d12 + 75)",
        "12 m, scavare 9 m, volare 24 m",
        "13",
        [
            23,
            10,
            21,
            14,
            13,
            17
        ]
    ],
    "Drago D’Ottone Giovane": [
        116,
        "Grande",
        "caotico buono",
        "17 (armatura naturale)",
        "110 (13d10 + 39)",
        "12 m, scavare 6 m, volare 24 m",
        "6",
        [
            19,
            10,
            17,
            12,
            11,
            15
        ]
    ],
    "Drago D’Ottone Cucciolo": [
        117,
        "Medio",
        "caotico buono",
        "16 (armatura naturale)",
        "16 (3d8 + 3)",
        "9 m, scavare 4,5 m, volare 18 m",
        "1",
        [
            15,
            10,
            13,
            10,
            11,
            13
        ]
    ]
}
SOURCE_FIELDS = {
    name: (*data[:7], tuple(data[7]))
    for name, data in _RAW_SPECS.items()
}
MONSTERS = {
    name: {
        "page": data[0], "size": data[1], "align": data[2],
        "ac": data[3], "hp": data[4], "speed": data[5],
        "gs": data[6],
        "abilities": dict(zip(("for", "des", "cos", "int", "sag", "car"), data[7])),
    }
    for name, data in SOURCE_FIELDS.items()
}

def audit(
    name: str,
    catalog: dict[str, Any] | None,
    existing_id: bool = False,
    same_name_monsters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if name not in SOURCE_FIELDS:
        raise ValueError("unknown_original_box")
    if existing_id or same_name_monsters:
        raise ValueError("duplicate_monster")
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGE_COUNT,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k,v in required.items()):
        raise ValueError("original_pdf_not_authorized")

    data = MONSTERS[name]
    actual = (
        data["page"], data["size"], data["align"], data["ac"],
        data["hp"], data["speed"], data["gs"],
        tuple(data["abilities"][score] for score in ("for", "des", "cos", "int", "sag", "car")),
    )
    if actual != SOURCE_FIELDS[name]:
        raise ValueError("source_fields_changed")
    hp_match = HP_RE.fullmatch(data["hp"])
    if hp_match is None:
        raise ValueError("invalid_hit_dice")
    avg, n, faces, bonus = hp_match.groups()
    if int(avg) != (int(n) * (int(faces) + 1)) // 2 + int(bonus or 0):
        raise ValueError("hit_dice_arithmetic_mismatch")
    if any(not 1 <= score <= 30 for score in actual[-1]):
        raise ValueError("ability_score_outside_range")
    attributes = {
        "classe_armatura": data["ac"], "punti_ferita": data["hp"],
        "velocita": data["speed"], "grado_sfida": data["gs"],
        "caratteristiche": {k:str(v) for k,v in data["abilities"].items()},
        "tipo_creatura": "Drago", "taglia": data["size"],
        "allineamento": data["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attributes):
        raise ValueError("global_numeric_or_identity_gate")
    page = data["page"]
    identity = "ref_" + hashlib.sha256(f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}".encode()).hexdigest()[:32]
    summary = (
        f"{name}. Drago {data['size']}, {data['align']}. "
        f"Classe Armatura {data['ac']}. Punti Ferita {data['hp']}. "
        f"Velocità {data['speed']}. Sfida {data['gs']}."
    )
    return {
        "id": identity, "name": name, "physical_page": page,
        "source_excerpt": summary,
        "source_text_checksum": hashlib.sha256(summary.encode()).hexdigest(),
        "attributes": deepcopy(attributes),
        "status": "source_verified_core_only",
        "writes": 0,
    }
