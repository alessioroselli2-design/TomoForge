"""Read-only source-specific review of misclassified Troll Feroce.

Original Italian boxed creature statblock appears completely on physical PDF
p59 (logical p259) in the licensed MPMM 201-294 segment. Historical 'ability'
and section_continues flag must be cleared only after the source is confirmed.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

ID = "ref_a41ee771f9fb58ed9d335d873d1364bc"
NAME = "Troll Feroce"
OWNER = "user_fabf28726a20"
SOURCE = "Mostri del multiverso 201-294.pdf"
CHECKSUM = "cff2f3231cc0cbf60771e9706d8a985d0b0ce8c522d8c9abee2acacd1d3a9e2e"
RAW_SHA = "d6c16813fc32686ae06d6d0e729876d7368a9103f1141365c40b805641c5c377"
ATTRIBUTES = {
    "classe_armatura": "15 (armatura naturale)",
    "punti_ferita": "172 (15d12 + 75)",
    "velocita": "12 m",
}
AUTHORITY = {
    "page": 59, "ruleset": "2014", "filename": SOURCE,
    "source_role": "authority", "logical_page": 259,
    "source_title": "Mordenkainen Presenta: Mostri del Multiverso",
    "source_status": "active", "authority_class": "licensed_translation",
    "logical_source_id": "mpmm_2022_it",
}


def inspect_troll_feroce(row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("source_candidate_absent")
    required = {
        "id": ID, "name": NAME, "source_name": NAME,
        "normalized_name": NAME.casefold(), "user_id": OWNER,
        "source_key": SOURCE, "source_language": "it",
        "source_text_checksum": CHECKSUM, "source_refs": [AUTHORITY],
        "reference_type": "ability", "review_status": "needs_review",
        "review_flags": ["sezione_potenzialmente_continua"],
        "canonical_id": None, "attributes": {}, "source_attributes": {},
        "review_corrections": {"_source_changed": True},
    }
    if any(row.get(k) != v for k, v in required.items()):
        raise ValueError("registered_original_source_drift")
    full = row.get("source_full_text")
    if not isinstance(full, str) or full != row.get("full_text"):
        raise ValueError("original_raw_drift")
    if hashlib.sha256(full.encode("utf-8")).hexdigest() != RAW_SHA:
        raise ValueError("registered_raw_sha_mismatch")
    if monster_identity_sanity_flags(NAME) or monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("source_statblock_semantic_gate_failed")
    # 15d12 + 75 yields floor(15*6.5+75) = 172
    if (15*(12+1))//2+75 != 172:
        raise ValueError("hit_dice_average_incoherent")
    return {
        "status": "eligible_exact_source_monster_reclassification",
        "name": NAME, "id": ID, "logical_page": 259,
        "source_statblock_contained_on_page": 59,
        "historical_section_flag_would_be_cleared_after_review": True,
        "attributes": ATTRIBUTES, "writes": 0,
    }
