"""Guarded canonical-text-only correction: MPMM Mago Apprendista PF OCR.

The owner's registered Italian MPMM source shows 13 (3d8), not the OCR
spacing artifact "1 3 (3d8)". Attributes already have correct 13 (3d8).
Preserve original OCR, original source attributes and checksum for provenance.
Do not promote, import, or write anything from this module.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

RECORD_ID = "ref_e14604cbec0a5306918cca5f4e74d639"
NAME = "Mago Apprendista"
SOURCE_KEY = "Mostri del multiverso 101-200.pdf"
LOGICAL_SOURCE_ID = "mpmm_2022_it"
RAW_HP = "1"
CORRECT_HP = "13 (3d8)"
BROKEN_FRAGMENT = "Punti Ferita 1 3 (3d8)"
CORRECT_FRAGMENT = "Punti Ferita 13 (3d8)"
SOURCE_CHECKSUM = "537f20d2894e606b77cff97f27805115f4d707cdcb232849bc9a3e40f2f4c54d"
WRITES = 0


def prepare_correction(record: dict[str, Any]) -> dict[str, Any]:
    """Return ONLY safe canonical prose edits, or fail on any drift."""
    if record.get("id") != RECORD_ID or record.get("name") != NAME:
        raise ValueError("record_identity_mismatch")
    if record.get("source_key") != SOURCE_KEY:
        raise ValueError("registered_source_mismatch")
    if record.get("review_status") != "verified":
        raise ValueError("review_status_changed")
    if record.get("source_text_checksum") != SOURCE_CHECKSUM:
        raise ValueError("source_evidence_checksum_mismatch")
    refs = record.get("source_refs") or []
    if not isinstance(refs, list) or {
        int(ref.get("logical_page") or 0)
        for ref in refs
        if isinstance(ref, dict) and ref.get("logical_source_id") == LOGICAL_SOURCE_ID
    } != {168, 169}:
        raise ValueError("original_pages_mismatch")
    attrs = record.get("attributes") or {}
    raw_attrs = record.get("source_attributes") or {}
    if (
        attrs.get("punti_ferita") != CORRECT_HP
        or raw_attrs.get("punti_ferita") != RAW_HP
        or attrs.get("classe_armatura") != "10 (13 con armatura magica)"
        or attrs.get("velocita") != "9 m"
    ):
        raise ValueError("hit_point_core_fields_mismatch")

    raw = record.get("source_full_text")
    if not isinstance(raw, str) or raw.count(BROKEN_FRAGMENT) != 1:
        raise ValueError("original_ocr_evidence_mismatch")
    checked = {}
    for key in ("full_text", "description"):
        value = record.get(key)
        if not isinstance(value, str) or value.count(BROKEN_FRAGMENT) != 1:
            raise ValueError("canonical_text_drift")
        checked[key] = value.replace(BROKEN_FRAGMENT, CORRECT_FRAGMENT, 1)

    # HP value 13 mathematically matches 3d8's average (3*4.5=13.5 -> 13).
    preserved_fields = {
        key: deepcopy(record.get(key))
        for key in ("source_full_text", "source_attributes", "source_refs", "source_text_checksum", "attributes")
    }
    return {
        **checked,
        "expected_original_fragment": BROKEN_FRAGMENT,
        "corrected_fragment": CORRECT_FRAGMENT,
        "preserve": preserved_fields,
        "status": "text_only_correction_ready_no_database_write",
        "writes": WRITES,
    }
