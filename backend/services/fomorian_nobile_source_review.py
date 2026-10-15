"""Fail-closed, source-only review of misclassified Bigby Fomorian Nobile."""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_ad2c8d2b58fd5cf3b4bff319b3784bbb"
SOURCE_FILE = "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf"
CHECKSUM = "cf7c6436ee76fd35deb4059bace6b121d60ae4458e341d021e356b2cf23fdb5d"
RAW_SHA256 = "7afecc4202d7ed9ac9e3d5b94a39251f9cd9884ffdbe980835ab10b5c241f133"
ATTRS = {
    "classe_armatura": "14 (17 con armatura magica)",
    "punti_ferita": "253 (22d12 + 110)",
    "velocita": "9 m",
}
AUTHORITY = {
    "page": 136, "logical_page": 136, "logical_source_id": "bgg_2023_it",
    "ruleset": "2014", "filename": SOURCE_FILE,
    "source_role": "authority", "source_status": "active",
    "authority_class": "licensed_translation",
    "source_title": "Bigby Presenta: La Gloria dei Giganti",
}


def assess_fomorian_nobile(record: dict[str, Any] | None) -> dict[str, Any]:
    """Propose no data writes; require exact original registered source snapshot."""
    if not isinstance(record, dict):
        raise ValueError("missing_fomorian_record")
    expected = {
        "id": RECORD_ID,
        "name": "Fomorian Nobile",
        "source_name": "Fomorian Nobile",
        "normalized_name": "fomorian nobile",
        "reference_type": "other",
        "source_language": "it",
        "source_key": SOURCE_FILE,
        "review_status": "needs_review",
        "review_flags": [],
        "canonical_id": None,
        "attributes": {},
        "source_attributes": {},
        "review_corrections": {"_source_changed": True},
        "source_text_checksum": CHECKSUM,
        "source_refs": [AUTHORITY],
    }
    if any(record.get(k) != v for k, v in expected.items()):
        raise ValueError("registered_source_snapshot_drift")
    original = record.get("source_full_text")
    if not isinstance(original, str) or original != record.get("full_text"):
        raise ValueError("original_description_drift")
    if hashlib.sha256(original.encode("utf-8")).hexdigest() != RAW_SHA256:
        raise ValueError("original_description_hash_drift")
    if "fomorian" not in original.lower() or len(original) < 150:
        raise ValueError("same_entity_description_unproven")
    # Original Italian Bigby PDF p136 (printed p135), named local stat block:
    # Huge giant wizard; CA14 (17 mage armor), HP253(22d12+110), speed9m,
    # CON20(+5). Visual page and independently extracted PDF text agree.
    if (22 * 13) // 2 + 22 * 5 != 253:
        raise ValueError("hit_point_formula_incoherent")
    if monster_semantic_numeric_flags(ATTRS):
        raise ValueError("strict_numeric_semantic_gate_failed")
    return {
        "status": "eligible_exact_record_reclassification",
        "source_page": 136,
        "old_type": "other",
        "new_type": "monster",
        "proposed_attributes": ATTRS,
        "source_unchanged": True,
        "writes": 0,
    }
