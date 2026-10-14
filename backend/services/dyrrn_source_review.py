"""Fail-closed exact registered-source review of Dyrrn, Eberron IT.

The recorded Italian text contains '3ld8' (lowercase letter l) as an OCR
confusion; the operational core has the correct 31d8 corroborated by the
original English edition. Preserve raw text and provenance unchanged.
No OCR gates are bypassed and this module performs no writes.
"""

from __future__ import annotations

from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_fd2857143c3b521c9204fc3032cf1d73"
SOURCE_CHECKSUM = "432f6cefc13a63c9553728e00d95cc10cba4996a723f95e986ec652442a10906"
ITALIAN_RAW = (
    "Aberrazione Media, caotico malvagio Classe Armatura 21 (armatura naturale) "
    "Punti Ferita 325 (3ld8 + 186) Velocità 12 m, volare 12 m (fluttuare)"
)
ATTRIBUTES = {
    "classe_armatura": "21 (armatura naturale)",
    "punti_ferita": "325 (31d8 + 186)",
    "velocita": "12 m, volare 12 m (fluttuare)",
}


def assess_dyrrn_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Require one exact pending Dyrrn record, two original authority pages."""
    if not isinstance(record, dict):
        raise ValueError("source_record_missing")
    if not all(
        (
            record.get("id") == RECORD_ID,
            record.get("name") == "Dyrrn",
            record.get("reference_type") == "monster",
            record.get("review_status") == "pending",
            record.get("canonical_id") is None,
            record.get("review_flags") == [
                "ocr_da_verificare", "source_guided_repair"
            ],
            record.get("source_text_checksum") == SOURCE_CHECKSUM,
            record.get("attributes") == ATTRIBUTES,
            record.get("full_text") == ITALIAN_RAW,
        )
    ):
        raise ValueError("source_snapshot_drift")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 2:
        raise ValueError("expected_exactly_two_authority_refs")
    if sorted(ref.get("page") for ref in refs if isinstance(ref, dict)) != [
        289, 291
    ]:
        raise ValueError("registered_physical_pages_drift")
    for ref in refs:
        if not isinstance(ref, dict) or not all(
            (
                ref.get("logical_page") == ref.get("page"),
                ref.get("logical_source_id") == "erlw_2019_it",
                ref.get("source_status") == "active",
                ref.get("source_role") == "authority",
                ref.get("authority_class") == "licensed_translation",
                ref.get("ruleset") == "2014",
                ref.get("filename") == "618795464-Eberron.pdf",
                ref.get("source_title") == "Eberron: Rinascita dopo l’Ultima Guerra",
            )
        ):
            raise ValueError("registered_source_authority_drift")

    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("numeric_gates_rejected")
    if (31 * (8 + 1)) // 2 + 186 != 325:
        raise ValueError("hit_dice_math_disagrees")
    # CON 22 (+6) x 31 hit dice = 186. English original has AC21, HP325
    # (31d8+186), Speed 40 ft./fly 40 ft. (hover), corresponding to 12 m.
    return {
        "status": "eligible_status_only_source_review",
        "source_id": "erlw_2019_it",
        "registered_pages": [289, 291],
        "raw_ocr_dice_is_preserved": True,
        "original_attributes_unchanged": True,
        "numeric_gates_passed": True,
        "source_snapshot_unchanged": True,
        "separate_editorial_adjudication_required": True,
    }
