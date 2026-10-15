"""Protected no-write review: wildfire spirit creature *and* its class feature.

The original Italian Tasha p38 contains a separate named creature statblock.
The original class_feature record remains intact and is not forcibly verified.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

ID = "ref_b48af5b5ccce202441ada1681016b71e"
FEATURE_ID = "ref_ae3e94213cfa52be8a5ab76654b078ad"
SOURCE_FILE = "Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf"
CATALOG_FILE = "Calderone-Omnicomprensivo-di-TASHA.pdf"
SOURCE_ID = "tce_2020_it"
PAGE = 38
NAME = "Spirito Della Fiamma"
SOURCE_TEXT = (
    "Elementale Piccolo Classe Armatura 13 (armatura naturale) "
    "Punti Ferita 5 + cinque volte il livello da druido del personaggio "
    "Velocità 9 m, volare 9 m (fluttuare)"
)
SHA = "42c51757bda965bad3cb9a738d6efa26182242eb1cd0b61aa97f6c21e6ee4c52"
CHECKSUM = "453c187dec611e54d7ac1c9c05572bc4eca08bb83c023ec93a1f465e63bf58e2"
ATTRS = {
    "classe_armatura": "13 (armatura naturale)",
    "punti_ferita": "5 + cinque volte il livello da druido del personaggio",
    "velocita": "9 m, volare 9 m (fluttuare)",
}
OCR_ATTRS = {"classe_armatura":"13 (armatura naturale)", "punti_ferita":"5", "velocita":"9 m, volare 9 m (fluttuare)"}


def audit_wildfire_statblock(
    new_record: dict[str, Any] | None,
    existing_monster: dict[str, Any] | None,
    original_feature: dict[str, Any] | None,
    source_catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    """Require exact registered class-feature evidence and zero monster duplicates."""
    if new_record is not None or existing_monster is not None:
        raise ValueError("monster_duplicate_or_candidate_id_collision")
    if not isinstance(original_feature, dict):
        raise ValueError("historical_class_feature_missing")
    expected = {
        "id": FEATURE_ID, "user_id": "user_fabf28726a20",
        "name": NAME, "source_name": NAME, "normalized_name": NAME.casefold(),
        "reference_type": "class_feature", "review_status": "pending",
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_language": "it", "source_key": SOURCE_FILE,
        "source_text_checksum": CHECKSUM,
        "attributes": ATTRS, "source_attributes": OCR_ATTRS,
        "source_refs": [{"page": PAGE, "filename": SOURCE_FILE}],
        "canonical_id": None,
    }
    if any(original_feature.get(k) != v for k, v in expected.items()):
        raise ValueError("historical_source_record_snapshot_drift")
    raw = original_feature.get("source_full_text")
    if not isinstance(raw, str) or raw != original_feature.get("full_text") or raw != SOURCE_TEXT:
        raise ValueError("source_excerpt_not_exactly_preserved")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != SHA:
        raise ValueError("source_sha256_not_exact")
    if not isinstance(source_catalog, dict):
        raise ValueError("missing_original_source_catalog")
    required = {
        "logical_source_id": SOURCE_ID, "physical_filename": CATALOG_FILE,
        "source_status": "active", "authority_class": "licensed_translation",
        "source_role": "authority",
    }
    if any(source_catalog.get(k) != v for k, v in required.items()):
        raise ValueError("licensed_pdf_source_catalog_mismatch")
    if not isinstance(source_catalog.get("physical_pages"), int) or source_catalog["physical_pages"] < PAGE:
        raise ValueError("statblock_source_page_out_of_range")
    token = f"{SOURCE_ID}|{SOURCE_FILE}|{PAGE}|{NAME.casefold()}"
    if "ref_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32] != ID:
        raise ValueError("source_record_id_nondeterministic")
    if monster_identity_sanity_flags(NAME) or monster_semantic_numeric_flags(ATTRS):
        raise ValueError("dynamic_druid_hp_or_identity_semantic_gate_failed")
    return {
        "status": "eligible_distinct_monster_statblock",
        "candidate_id": ID, "original_feature_id": FEATURE_ID,
        "name": NAME, "page": PAGE, "attributes": ATTRS,
        "class_feature_left_unchanged": True,
        "source_raw_preserved": True, "writes": 0,
    }
