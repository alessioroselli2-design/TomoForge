"""Read-only Italian Monster Manual original boxed statblocks, physical pp 161–162.

Direct high-resolution visual reading of the owner's licensed 353-page
image-only PDF with SHA-256 matched to registered active authority.
Each named boxed creature is independent, even when sharing a PDF page.
Only concise essential stats and action labels; NOT complete actions, traits,
spell descriptions or legendary mechanics. No database writes, no PDF assets.
"""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import (
    monster_identity_sanity_flags, monster_semantic_numeric_flags,
)

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PDF_PAGES = 353
HP = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_ORIGINAL: dict[str, dict[str, Any]] = {
    "Githyanki Combattente": {
        "page": 161,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "gith",
        "align": "legale malvagio",
        "ac": "17 (mezza armatura)",
        "hp": "49 (9d8 + 9)",
        "speed": "9 m",
        "gs": "3",
        "scores": [
            15,
            14,
            12,
            13,
            13,
            10
        ],
        "actions": [
            "Multiattacco",
            "Spadone"
        ]
    },
    "Githyanki Cavaliere": {
        "page": 161,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "gith",
        "align": "legale malvagio",
        "ac": "18 (armatura completa)",
        "hp": "91 (14d8 + 28)",
        "speed": "9 m",
        "gs": "8",
        "scores": [
            16,
            14,
            15,
            14,
            14,
            15
        ],
        "actions": [
            "Multiattacco",
            "Spadone D'Argento"
        ]
    },
    "Githzerai Monaco": {
        "page": 162,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "gith",
        "align": "legale neutrale",
        "ac": "14",
        "hp": "38 (7d8 + 7)",
        "speed": "9 m",
        "gs": "2",
        "scores": [
            12,
            15,
            12,
            13,
            14,
            10
        ],
        "actions": [
            "Multiattacco",
            "Colpo Senz'Armi"
        ]
    },
    "Githzerai Zerth": {
        "page": 162,
        "type": "Umanoide",
        "size": "Medio",
        "subtype": "gith",
        "align": "legale neutrale",
        "ac": "17",
        "hp": "84 (13d8 + 26)",
        "speed": "9 m",
        "gs": "6",
        "scores": [
            13,
            18,
            15,
            16,
            17,
            12
        ],
        "actions": [
            "Multiattacco",
            "Colpo Senz'Armi"
        ]
    }
}
SEALED = {
    n: (
        d["page"], d["type"], d["size"], d.get("subtype", ""),
        d["align"], d["ac"], d["hp"], d["speed"], d["gs"],
        tuple(d["scores"]), tuple(d["actions"]),
    )
    for n, d in _ORIGINAL.items()
}
CREATURES = deepcopy(_ORIGINAL)


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    existing_id: bool = False,
    existing_monsters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PDF_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in required.items()):
        raise ValueError("registered_authority_changed")
    if existing_id or existing_monsters:
        raise ValueError("duplicate_monster")
    if name not in SEALED:
        raise ValueError("not_independent_original_monster")
    data = CREATURES[name]
    core = (
        data["page"], data["type"], data["size"], data.get("subtype", ""),
        data["align"], data["ac"], data["hp"], data["speed"], data["gs"],
        tuple(data["scores"]), tuple(data["actions"]),
    )
    if core != SEALED[name]:
        raise ValueError("sealed_statblock_changed")
    match = HP.fullmatch(data["hp"])
    if match is None:
        raise ValueError("invalid_source_hit_dice")
    average, count, faces, op, value = match.groups()
    bonus = int(value or 0) * (-1 if op == "-" else 1)
    if int(average) != int(count) * (int(faces) + 1) // 2 + bonus:
        raise ValueError("incorrect_hit_dice_average")
    if len(data["scores"]) != 6 or any(
        not isinstance(score, int) or not 1 <= score <= 30 for score in data["scores"]
    ):
        raise ValueError("six_characteristics_invalid")
    attrs = {
        "classe_armatura": data["ac"],
        "punti_ferita": data["hp"],
        "velocita": data["speed"],
        "grado_sfida": data["gs"],
        "caratteristiche": dict(zip(
            ("for", "des", "cos", "int", "sag", "car"),
            (str(v) for v in data["scores"]),
        )),
        "tipo_creatura": data["type"],
        "taglia": data["size"],
        "allineamento": data["align"],
        "azioni_nomi_da_completare": list(data["actions"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if data.get("subtype"):
        attrs["sottotipo_creatura"] = data["subtype"]
    if name == "Gigante Delle Nuvole":
        attrs["allineamento_varianti_percentuali"] = {
            "neutrale buono": 50, "neutrale malvagio": 50,
        }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("identity_or_numeric_gate_failed")
    physical_page = data["page"]
    source_key = f"{SOURCE_ID}|{FILENAME}|{physical_page}|{name.casefold()}"
    summary = (
        f"{name}. {data['type']} {data['size']}, {data['align']}. "
        f"Classe Armatura {data['ac']}. Punti Ferita {data['hp']}. "
        f"Velocità {data['speed']}. Sfida {data['gs']}."
    )
    return {
        "id": "ref_" + hashlib.sha256(source_key.encode()).hexdigest()[:32],
        "name": name, "physical_page": physical_page,
        "source_excerpt": summary,
        "source_text_checksum": hashlib.sha256(summary.encode()).hexdigest(),
        "attributes": deepcopy(attrs),
        "status": "original_source_core_only", "writes": 0,
    }
