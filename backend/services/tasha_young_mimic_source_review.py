"""Tasha Italian licensed PDF: read-only missing Young Mimic source review.

A numbered original PDF page was inspected visually; this concise textual
transcription is a manual source excerpt, *not* successful automatic OCR.
"""
from __future__ import annotations
import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

ID = "ref_28b6c039ecf9cc1b7f2e4efd208f21d7"
NAME = "Mimic Giovane"
SOURCE_FILE = "Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf"
CATALOG_FILE = "Calderone-Omnicomprensivo-di-TASHA.pdf"
SOURCE_ID = "tce_2020_it"
PAGE = 166
EXCERPT = "Mostruosità Minuscola (mutaforma) Classe Armatura 11 Punti Ferita 7 (2d4 + 2) Velocità 3 m, scalare 3 m"
EXCERPT_SHA256 = "0d79cd619fa5f1c1d82f128e834150bed892792108eecd6089505202f088204e"
ATTRS = {"classe_armatura": "11", "punti_ferita": "7 (2d4 + 2)", "velocita": "3 m, scalare 3 m"}


def audit_young_mimic(
    record_by_id: dict[str, Any] | None,
    matching_name_rows: list[dict[str, Any]],
    source: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return no-write verdict only when source, identity and math agree."""
    if record_by_id is not None or matching_name_rows:
        raise ValueError("duplicate_or_colliding_mimic_record")
    if not isinstance(source, dict):
        raise ValueError("source_catalog_unavailable")
    expected = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": CATALOG_FILE,
        "source_status": "active",
        "authority_class": "licensed_translation",
        "source_role": "authority",
    }
    if any(source.get(key) != value for key, value in expected.items()):
        raise ValueError("registered_licensed_source_mismatch")
    if not isinstance(source.get("physical_pages"), int) or source["physical_pages"] < PAGE:
        raise ValueError("registered_source_page_unavailable")
    if hashlib.sha256(EXCERPT.encode("utf-8")).hexdigest() != EXCERPT_SHA256:
        raise ValueError("registered_manual_excerpt_sha_drift")
    token = f"{SOURCE_ID}|{SOURCE_FILE}|{PAGE}|{NAME.casefold()}"
    if "ref_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32] != ID:
        raise ValueError("new_source_id_drift")
    if monster_identity_sanity_flags(NAME) or monster_semantic_numeric_flags(ATTRS):
        raise ValueError("global_identity_or_numeric_gate_failed")
    if (2 * (4 + 1)) // 2 + 2 != 7:
        raise ValueError("manual_hit_dice_formula_mismatch")
    return {
        "status": "eligible_manual_visual_source_registration",
        "record_id": ID, "name": NAME, "page": PAGE,
        "source": SOURCE_ID, "attributes": ATTRS,
        "original_manual_transcription": True,
        "automatic_ocr_not_claimed": True,
        "writes": 0,
    }
