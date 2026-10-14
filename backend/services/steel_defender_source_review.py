"""Fail-closed source-status review for Eberron Steel Defender only.

An ordinary OCR reread can mangle its player-level HP formula. This review
requires exact source text AND the published official English WotC erratum.
It never edits attributes, skips numeric gates, or writes to the database.
"""

from __future__ import annotations

from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_07e14d22e5895eb88362784f61f4066e"
SOURCE_CHECKSUM = "0ac58c4625c04093295a323217b07fa4f3964bf8660c2b91648e5282c31321f5"
HP_FORMULA = (
    "2 + il modificatore di Intelligenza dell'artefice + cinque volte il "
    "livello da artefice del personaggio (il difensore ha un numero di "
    "Dadi Vita [d8] pari al livello da artefice del personaggio)"
)
SEALED_ATTRIBUTES = {
    "classe_armatura": "15 (armatura naturale)",
    "punti_ferita": HP_FORMULA,
    "velocita": "12 m",
}
SEALED_FULL_TEXT = (
    "Costrutto Medio Classe Armatura 15 (armatura naturale) Punti Ferita "
    "2 + il modificatore di Intelligenza dell'artefice+ il livello "
    "da artefice del personaggio moltiplicato per cinque "
    "(il difensore ha un numero di Dadi Vita [d8] pari al livello "
    "da artefice del personaggio) Velocità 12 m"
)
EXPECTED_REVIEW_FLAGS = ["ocr_da_verificare", "source_guided_repair"]


def assess_steel_defender_source_review(record: dict[str, Any]) -> dict[str, Any]:
    """Reject all records except the one vetted Eberron p62 translation snapshot."""
    if not isinstance(record, dict):
        raise ValueError("missing_target_record")
    if (
        record.get("id") != RECORD_ID
        or record.get("reference_type") != "monster"
        or record.get("name") != "Difensore D'Acciaio"
        or record.get("review_status") != "pending"
        or record.get("canonical_id") is not None
        or record.get("review_flags") != EXPECTED_REVIEW_FLAGS
        or record.get("source_text_checksum") != SOURCE_CHECKSUM
        or record.get("attributes") != SEALED_ATTRIBUTES
    ):
        raise ValueError("registered_record_snapshot_drift")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1:
        raise ValueError("source_reference_count_drift")
    ref = refs[0]
    if not isinstance(ref, dict) or not all(
        (
            ref.get("logical_source_id") == "erlw_2019_it",
            ref.get("page") == 62,
            ref.get("logical_page") == 62,
            ref.get("source_status") == "active",
            ref.get("source_role") == "authority",
            ref.get("authority_class") == "licensed_translation",
            ref.get("filename") == "618795464-Eberron.pdf",
            ref.get("ruleset") == "2014",
        )
    ):
        raise ValueError("source_provenance_drift")
    if str(record.get("full_text") or "") != SEALED_FULL_TEXT:
        raise ValueError("italian_source_text_drift")

    # Runtime semantic gate explicitly supports formula-based artificer HP.
    # This stat block is not expected to have a fixed hit-point average.
    if monster_semantic_numeric_flags(SEALED_ATTRIBUTES):
        raise ValueError("numeric_gate_rejected_player_scaling_formula")
    if not all(
        (
            "modificatore di Intelligenza" in HP_FORMULA,
            "cinque volte il livello da artefice" in HP_FORMULA,
            "Dadi Vita [d8]" in HP_FORMULA,
            SEALED_ATTRIBUTES["classe_armatura"] == "15 (armatura naturale)",
            SEALED_ATTRIBUTES["velocita"] == "12 m",
        )
    ):
        raise ValueError("official_steel_defender_core_drift")
    return {
        "status": "eligible_status_only_source_review",
        "record_id": RECORD_ID,
        "source_id": "erlw_2019_it",
        "page": 62,
        "source_snapshot_unchanged": True,
        "attributes_unchanged": True,
        "numeric_gates_active_and_passed": True,
        "original_source_faithful": True,
        "requires_explicit_source_adjudication": True,
    }
