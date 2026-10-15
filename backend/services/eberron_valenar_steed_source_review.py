"""Read-only source and duplicate gate for Eberron's Valenar Steed.

The separately named original Italian PDF page 285 was visually inspected.
No database writes, inferred OCR agreement, or generic-name canonicalization.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import (
    monster_identity_sanity_flags,
    monster_semantic_numeric_flags,
)

NAME = "Destriero Valenar"
ID = "ref_91a87d5fc66973078e75cd06c6b19c28"
SOURCE = "618795464-Eberron.pdf"
SOURCE_ID = "erlw_2019_it"
PAGE = 285
EXCERPT = (
    "Folletto Grande, neutrale Classe Armatura 13 "
    "Punti Ferita 22 (3d10 + 6) Velocità 18 m"
)
DIGEST = "f162e380496570555096b273e6bc50cd50df3f3af09241a79ac7534c98c93c97"
ATTRIBUTES = {
    "classe_armatura": "13",
    "punti_ferita": "22 (3d10 + 6)",
    "velocita": "18 m",
}


def validate_valenar_source(
    existing_id: dict[str, Any] | None,
    existing_name: list[dict[str, Any]],
    source_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return an eligible no-write verdict only for the sealed absent entity."""
    if existing_id is not None or existing_name:
        raise ValueError("existing_monster_or_id_collision")
    if not isinstance(source_metadata, dict):
        raise ValueError("missing_registered_source")
    expected = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": SOURCE,
        "source_status": "active",
        "authority_class": "licensed_translation",
        "source_role": "authority",
    }
    if any(source_metadata.get(k) != v for k, v in expected.items()):
        raise ValueError("source_provenance_mismatch")
    page_count = source_metadata.get("physical_pages")
    if not isinstance(page_count, int) or page_count < PAGE:
        raise ValueError("source_page_not_available")
    if hashlib.sha256(EXCERPT.encode("utf-8")).hexdigest() != DIGEST:
        raise ValueError("primary_source_transcription_drift")
    token = f"{SOURCE_ID}|{SOURCE}|{PAGE}|{NAME.casefold()}"
    if "ref_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32] != ID:
        raise ValueError("deterministic_source_id_mismatch")
    if monster_identity_sanity_flags(NAME):
        raise ValueError("candidate_identity_invalid")
    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("strict_numeric_gate_failed")
    if (3 * 11) // 2 + 6 != 22:
        raise ValueError("hit_dice_and_constitution_mismatch")
    return {
        "status": "eligible_new_source_record_review",
        "id": ID,
        "name": NAME,
        "source_page": PAGE,
        "registered_logical_source": SOURCE_ID,
        "attributes": ATTRIBUTES,
        "source_excerpt_sha256": DIGEST,
        "record_absent": True,
        "writes": 0,
    }
