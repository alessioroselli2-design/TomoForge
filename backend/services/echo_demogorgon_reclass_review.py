"""Fail-closed, no-write reclassification audit for Bigby IT Echo of Demogorgon.

A pre-existing record was misclassified as 'other'; never make a duplicate.
The original registered description is retained. Numeric attributes come from
the same-name stat block on original licensed Bigby Italian PDF page 130.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_2e7ffa9c08ab50628da4dd5424358f07"
SOURCE = "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf"
SOURCE_CHECKSUM = "5fa7c9178b7c7cb59688d967294f04d57ffed44cdde48510a517e7816133aa20"
RAW_SHA256 = "9cdf1f4243637ba27b766c777965bdba5bac4478471eb267ba834fdc9f476e63"
AUTHORITY = {
    "page": 130, "logical_page": 130, "logical_source_id": "bgg_2023_it",
    "ruleset": "2014", "filename": SOURCE, "source_role": "authority",
    "source_status": "active", "authority_class": "licensed_translation",
    "source_title": "Bigby Presenta: La Gloria dei Giganti",
}
ATTRIBUTES = {
    "classe_armatura": "14 (armatura naturale)",
    "punti_ferita": "85 (10d10 + 30)",
    "velocita": "12 m",
}


def assess_existing_echo_record(record: dict[str, Any] | None) -> dict[str, Any]:
    """Fail closed if the existing description or provenance has drifted."""
    if not isinstance(record, dict):
        raise ValueError("echo_record_absent")
    expected = {
        "id": RECORD_ID,
        "name": "Eco Di Demogorgon",
        "source_name": "Eco Di Demogorgon",
        "normalized_name": "eco di demogorgon",
        "reference_type": "other",
        "source_language": "it",
        "source_key": SOURCE,
        "review_status": "needs_review",
        "review_flags": [],
        "canonical_id": None,
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": {},
        "source_attributes": {},
        "review_corrections": {"_source_changed": True},
        "source_refs": [AUTHORITY],
    }
    if any(record.get(k) != value for k, value in expected.items()):
        raise ValueError("sealed_existing_echo_snapshot_drift")
    original_text = record.get("source_full_text")
    if not isinstance(original_text, str) or original_text != record.get("full_text"):
        raise ValueError("original_description_changed")
    if hashlib.sha256(original_text.encode("utf-8")).hexdigest() != RAW_SHA256:
        raise ValueError("original_description_sha256_changed")
    if not all((
        "Demogorgon" in original_text,
        "ettin" in original_text.lower(),
        len(original_text) > 250,
    )):
        raise ValueError("source_description_semantics_failed")
    # Original Italian p130 local named statblock: large fiend/demon,
    # AC14 natural, HP85(10d10+30), speed12m, CON17(+3).
    # Independent PDF text layer and visual original glyph check agree.
    if (10 * (10 + 1)) // 2 + 10 * 3 != 85:
        raise ValueError("average_hit_dice_inconsistent")
    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("global_monster_numeric_gate_failed")
    return {
        "status": "eligible_exact_record_reclassification",
        "original_type": "other",
        "proposed_type": "monster",
        "source_page": 130,
        "stats": ATTRIBUTES,
        "original_raw_preserved": True,
        "original_source_attributes_preserved": True,
        "writes": 0,
    }
