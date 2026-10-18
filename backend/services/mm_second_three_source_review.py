"""Source-locked, read-only proof for MM pages 19–21 (Ankheg/Arpia/Artiglio).

The original licensed Italian 353-page Monster Manual was rechecked locally by
whole-file SHA-256, original-page visual review, and two bounded OCR modes.
Raw scanned pages and bulk OCR text remain private and are not committed.
No database writes or automatic OCR promotion take place here.
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

MANUAL = "847921086-Manuale-Dei-Mostri-5e.pdf"
SOURCE_ID = "mm_2014_it"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
EXPECTED_PAGES = 353
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")

MONSTERS: dict[str, dict[str, Any]] = {
    "Ankheg": {
        "id": "ref_d7ce1b988d901d2bf56c9d64a94f6a80",
        "page": 19,
        "kind": "Mostruosità Grande",
        "alignment": "senza allineamento",
        "ac": "14 (armatura naturale), 11 se prono",
        "hp": "39 (6d10 + 6)",
        "speed": "9 m, scavare 3 m",
        "challenge": "2",
        "abilities": {
            "for": "17", "des": "11", "cos": "13",
            "int": "1", "sag": "13", "car": "6",
        },
        "excerpt_sha256": "9ce0e3c3771b959e816f5abb5ef16c4fa5f5b5eee8c79ee70a61ae54d812859d",
    },
    "Arpia": {
        "id": "ref_0beb8b912522853120675dab6a4a5959",
        "page": 20,
        "kind": "Mostruosità Media",
        "alignment": "caotico malvagio",
        "ac": "11",
        "hp": "38 (7d8 + 7)",
        "speed": "6 m, volare 12 m",
        "challenge": "1",
        "abilities": {
            "for": "12", "des": "13", "cos": "12",
            "int": "7", "sag": "10", "car": "13",
        },
        "excerpt_sha256": "d63c96dd02ef674352d5a436f67424fc770c0736bea6bfb9d5b49ccec36ba91c",
    },
    "Artiglio Strisciante": {
        "id": "ref_cf0cf8dac94cf42c1db1e8868583300a",
        "page": 21,
        "kind": "Non morto Minuscolo",
        "alignment": "neutrale malvagio",
        "ac": "12",
        "hp": "2 (1d4)",
        "speed": "6 m, scalare 6 m",
        "challenge": "0",
        "abilities": {
            "for": "13", "des": "14", "cos": "11",
            "int": "5", "sag": "10", "car": "4",
        },
        "excerpt_sha256": "af4eb5dcce83e432e2be7795c37b560ee09341b62c6a1cbce61577ba50d4f896",
    },
}


def _excerpt(name: str, spec: dict[str, Any]) -> str:
    return (
        f"{name}. {spec['kind']}, {spec['alignment']}. "
        f"Classe Armatura {spec['ac']}. "
        f"Punti Ferita {spec['hp']}. "
        f"Velocità {spec['speed']}. Sfida {spec['challenge']}."
    )


def audit_mm_second_batch(
    name: str,
    existing_id: dict[str, Any] | None,
    existing_names: list[dict[str, Any]],
    catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unknown_proposed_monster")
    if existing_id is not None or existing_names:
        raise ValueError("duplicate_record_or_name")
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": MANUAL,
        "physical_sha256": SHA256,
        "physical_pages": EXPECTED_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(key) != value for key, value in required.items()
    ):
        raise ValueError("authority_drift")

    spec = MONSTERS[name]
    if spec["page"] not in (19, 20, 21):
        raise ValueError("not_in_three_page_source_window")
    token = f"{SOURCE_ID}|{MANUAL}|{spec['page']}|{name.casefold()}"
    computed_id = "ref_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
    if spec["id"] != computed_id:
        raise ValueError("deterministic_source_identity_drift")

    short = _excerpt(name, spec)
    checksum = hashlib.sha256(short.encode("utf-8")).hexdigest()
    if checksum != spec["excerpt_sha256"]:
        raise ValueError("sealed_visual_evidence_changed")

    attributes = {
        "classe_armatura": spec["ac"],
        "punti_ferita": spec["hp"],
        "velocita": spec["speed"],
        "grado_sfida": spec["challenge"],
        "caratteristiche": spec["abilities"],
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attributes):
        raise ValueError("semantic_gate_failed")
    parsed = HP_RE.fullmatch(spec["hp"])
    if parsed is None:
        raise ValueError("unreadable_hit_dice")
    avg, count, faces, mod = parsed.groups()
    if int(avg) != (int(count) * (int(faces) + 1)) // 2 + int(mod or 0):
        raise ValueError("incoherent_hit_dice")
    stats = spec["abilities"]
    if set(stats) != {"for", "des", "cos", "int", "sag", "car"}:
        raise ValueError("abilities_incomplete")
    if any(not v.isdigit() or not 1 <= int(v) <= 30 for v in stats.values()):
        raise ValueError("abilities_out_of_bounds")

    return {
        "status": "eligible_source_confirmed_statblock",
        "id": computed_id,
        "name": name,
        "physical_page": spec["page"],
        "source_excerpt": short,
        "source_text_checksum": checksum,
        "attributes": deepcopy(attributes),
        "ocr_is_not_auto_verified": True,
        "writes": 0,
    }
