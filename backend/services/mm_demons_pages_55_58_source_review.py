"""Six original Italian Monster Manual demon blocks on physical pages 55-58.

Source-file SHA-256 matches the registered licensed 353-page PDF. Physical
pages 50-54 carry demon lore, not independent statblocks. On p57 and p58,
two distinct boxed statblocks must not be collapsed into a single creature.
This module checks provenance and core stats and performs NO DB writes.
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
PAGES = 353
DICE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: [+] ([0-9]+))?[)]$")

MONSTERS: dict[str, dict[str, Any]] = {
    "Balor": {
        "page": 55, "kind": "Immondo Enorme (demone)", "type": "Immondo",
        "size": "Enorme", "align": "caotico malvagio",
        "ac": "19 (armatura naturale)", "hp": "262 (21d12 + 126)",
        "speed": "12 m, volare 24 m", "gs": "19",
        "abilities": {"for": "26", "des": "15", "cos": "22", "int": "20", "sag": "16", "car": "22"},
        "id": "ref_7f6fa689d20a2413713896b8c6293b7c",
        "digest": "ccfe8c954d091e0d0a260a17f487e775de8b044fcf00645de80d5d7b8c46ce01",
    },
    "Barlgura": {
        "page": 56, "kind": "Immondo Grande (demone)", "type": "Immondo",
        "size": "Grande", "align": "caotico malvagio",
        "ac": "15 (armatura naturale)", "hp": "68 (8d10 + 24)",
        "speed": "12 m, scalare 12 m", "gs": "5",
        "abilities": {"for": "18", "des": "15", "cos": "16", "int": "7", "sag": "14", "car": "9"},
        "id": "ref_384ddc2ff29212ef4140a09c116c0786",
        "digest": "c3e99c751a3048ffe1828768f7ce1b01451ace60e6e2f809add884ee0bea2f32",
    },
    "Chasme": {
        "page": 57, "kind": "Immondo Grande (demone)", "type": "Immondo",
        "size": "Grande", "align": "caotico malvagio",
        "ac": "15 (armatura naturale)", "hp": "84 (13d10 + 13)",
        "speed": "6 m, volare 18 m", "gs": "6",
        "abilities": {"for": "15", "des": "15", "cos": "12", "int": "11", "sag": "14", "car": "10"},
        "id": "ref_2a366d4ae9ad5d08e4789d6702a15a4b",
        "digest": "455055f3d77161df8cff6130e7c20d8cfc29665c81e55fc7a4af4d78f4496295",
    },
    "Demone D'Ombra": {
        "page": 57, "kind": "Immondo Medio (demone)", "type": "Immondo",
        "size": "Medio", "align": "caotico malvagio",
        "ac": "13", "hp": "66 (12d8 + 12)",
        "speed": "9 m, volare 9 m", "gs": "4",
        "abilities": {"for": "1", "des": "17", "cos": "12", "int": "14", "sag": "13", "car": "14"},
        "id": "ref_f9635854ca926fc8b20e45270f76e05c",
        "digest": "cbd916c47f305a93bae2cecdc2ee35a4634330132da02f3597867c027f7c420f",
    },
    "Dretch": {
        "page": 58, "kind": "Immondo Piccolo (demone)", "type": "Immondo",
        "size": "Piccolo", "align": "caotico malvagio",
        "ac": "11 (armatura naturale)", "hp": "18 (4d6 + 4)",
        "speed": "6 m", "gs": "1/4",
        "abilities": {"for": "11", "des": "11", "cos": "12", "int": "5", "sag": "8", "car": "3"},
        "id": "ref_5320557f482c3b7011568d6ffc4ac017",
        "digest": "b5781266c83e6762f41adf3f08b3da139877899ee2afa2073603db1e258f71b7",
    },
    "Glabrezu": {
        "page": 58, "kind": "Immondo Grande (demone)", "type": "Immondo",
        "size": "Grande", "align": "caotico malvagio",
        "ac": "17 (armatura naturale)", "hp": "157 (15d10 + 75)",
        "speed": "12 m", "gs": "9",
        "abilities": {"for": "20", "des": "15", "cos": "21", "int": "19", "sag": "17", "car": "16"},
        "id": "ref_1b91ece1efd530330c9cde5217f34cf0",
        "digest": "1e601a1e50a2cecdc15e1cbeac15cf081b16e87c873b48c517b944dffbfd4cd6",
    },
}


def concise(name: str, data: dict[str, Any]) -> str:
    return (
        f"{name}. {data['kind']}, {data['align']}. "
        f"Classe Armatura {data['ac']}. Punti Ferita {data['hp']}. "
        f"Velocità {data['speed']}. Sfida {data['gs']}."
    )


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    record_exists: bool = False,
    same_name_monsters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if name not in MONSTERS:
        raise ValueError("unknown_original_demon")
    if record_exists or same_name_monsters:
        raise ValueError("already_present_as_monster")
    expected = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(k) != value for k, value in expected.items()
    ):
        raise ValueError("original_authority_drift")
    d = MONSTERS[name]
    if d["page"] not in (55, 56, 57, 58):
        raise ValueError("source_page_out_of_scope")
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    actual_id = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if actual_id != d["id"]:
        raise ValueError("deterministic_identity_changed")
    excerpt = concise(name, d)
    actual_digest = hashlib.sha256(excerpt.encode()).hexdigest()
    if actual_digest != d["digest"]:
        raise ValueError("sealed_source_fields_changed")
    attributes = {
        "classe_armatura": d["ac"], "punti_ferita": d["hp"],
        "velocita": d["speed"], "grado_sfida": d["gs"],
        "caratteristiche": d["abilities"], "tipo_creatura": d["type"],
        "taglia": d["size"], "allineamento": d["align"],
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attributes):
        raise ValueError("numeric_or_identity_gate_failed")
    match = DICE.fullmatch(d["hp"])
    if not match:
        raise ValueError("hit_dice_not_parseable")
    avg, count, faces, bonus = match.groups()
    if int(avg) != int(count) * (int(faces) + 1) // 2 + int(bonus or 0):
        raise ValueError("incorrect_hit_dice_math")
    if set(d["abilities"]) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not v.isdigit() or not 1 <= int(v) <= 30 for v in d["abilities"].values()
    ):
        raise ValueError("six_abilities_invalid")
    return {
        "id": actual_id, "name": name, "physical_page": d["page"],
        "source_excerpt": excerpt, "source_text_checksum": actual_digest,
        "attributes": deepcopy(attributes),
        "status": "eligible_source_checked_core_statblock", "writes": 0,
    }
