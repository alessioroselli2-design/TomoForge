"""Exact fail-closed source adjudication for Rak Tulkhesh, Eberron IT.

This does not change ordinary OCR or numeric gates and cannot write records.
The registered raw dice '33dl2' is preserved; the English original and
CON +8 × 33 dice independently substantiate operational 33d12 + 264.
"""

from __future__ import annotations

from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_2f64f571e368521f9ab39c4d6bd898d3"
SOURCE_CHECKSUM = "d012b36e5d51df164ec6749fd27591b13326f0598d7ed564ce11ca446dc031c0"
ITALIAN_RAW = (
    "Immondo Enorme, neutrale malvagio Classe Armatura 23 (armatura naturale; "
    "25 contro attacchi a distanza) Punti Ferita 478 (33dl2 + 264) Velocità "
    "12 m, scalare 12 m, volare 24 m"
)
ATTRIBUTES = {
    "classe_armatura": "23 (armatura naturale; 25 contro attacchi a distanza)",
    "punti_ferita": "478 (33d12 + 264)",
    "velocita": "12 m, scalare 12 m, volare 24 m",
}


def assess_rak_tulkhesh_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Require exact record, text, attributes and both source authority pages."""
    if not isinstance(record, dict):
        raise ValueError("missing_registered_record")
    if not all(
        (
            record.get("id") == RECORD_ID,
            record.get("name") == "Rak Tulkhesh",
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
        raise ValueError("registered_source_record_drift")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 2:
        raise ValueError("source_ref_count_drift")
    if sorted(ref.get("page") for ref in refs if isinstance(ref, dict)) != [
        313, 314
    ]:
        raise ValueError("registered_pages_drift")
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
            raise ValueError("registered_authority_source_drift")
    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("global_numeric_gate_failed")
    if (33 * (12 + 1)) // 2 + 264 != 478 or 33 * 8 != 264:
        raise ValueError("hit_dice_math_disagrees")
    # English ERLW p303: AC23 (natural), AC25 versus ranged attacks,
    # HP478 (33d12 +264), speed40/climb40/fly80 ft. (12/12/24 m).
    return {
        "status": "eligible_status_only_source_review",
        "source_id": "erlw_2019_it",
        "pages": [313, 314],
        "original_attributes_unchanged": True,
        "original_raw_dice_preserved": True,
        "numeric_gates_passed": True,
        "snapshot_unchanged": True,
        "separate_editorial_adjudication_required": True,
    }
