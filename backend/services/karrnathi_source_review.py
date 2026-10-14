"""Fail-closed registered-source adjudication for Karrnathi Undead only.

The two layout OCR readers could not agree reliably on a rendering.
This procedure uses the unmodified, exact Italian registered source, a
corroborated English original and the unchanged global numeric gates.
It NEVER updates a record or weakens the ordinary OCR workflow.
"""

from __future__ import annotations

from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_b6af0f71247d5a4a8804486807d83776"
SOURCE_CHECKSUM = "fa517173161dacd7b164b24e15871a98d0e96bfc11a952e43acc8ce377a12657"
ATTRIBUTES = {
    "classe_armatura": "17 (mezza armatura)",
    "punti_ferita": "52 (7d8 + 21)",
    "velocita": "9 m",
}
ITALIAN_RAW = (
    "Non morto Medio, legale malvagio Classe Armatura 17 (mezza armatura) "
    "Punti Ferita 52 (7d8 + 21) Velocità 9 m"
)
# Eberron: Rising from the Last War, Karrnathi Undead Soldier (English p. 295).
# Independent transcriptions corroborate AC 17 half plate, HP 52 (7d8+21),
# Speed 30 ft., conventionally 9 m in the Italian 2014 ruleset.
ENGLISH_CORE = (17, 52, 7, 8, 21, 30)


def assess_karrnathi_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Exact, single-record source review; reject any snapshot/provenance drift."""
    if not isinstance(record, dict):
        raise ValueError("missing_registered_record")
    if (
        record.get("id") != RECORD_ID
        or record.get("name") != "Non Morto Karrnathi"
        or record.get("reference_type") != "monster"
        or record.get("review_status") != "pending"
        or record.get("canonical_id") is not None
        or record.get("review_flags") != []
        or record.get("source_text_checksum") != SOURCE_CHECKSUM
        or record.get("attributes") != ATTRIBUTES
        or record.get("full_text") != ITALIAN_RAW
    ):
        raise ValueError("registered_snapshot_drift")

    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1:
        raise ValueError("authority_source_count_drift")
    ref = refs[0]
    if not isinstance(ref, dict) or not all(
        (
            ref.get("page") == 316,
            ref.get("logical_page") == 316,
            ref.get("logical_source_id") == "erlw_2019_it",
            ref.get("source_status") == "active",
            ref.get("source_role") == "authority",
            ref.get("authority_class") == "licensed_translation",
            ref.get("filename") == "618795464-Eberron.pdf",
            ref.get("ruleset") == "2014",
            ref.get("source_title") == "Eberron: Rinascita dopo l’Ultima Guerra",
        )
    ):
        raise ValueError("registered_source_authority_drift")

    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("numeric_quality_gate_rejected")
    ac, hp, count, size, modifier, speed_feet = ENGLISH_CORE
    if (
        ac != 17
        or hp != 52
        or (count * (size + 1)) // 2 + modifier != hp
        or speed_feet != 30
        or ATTRIBUTES["classe_armatura"] != "17 (mezza armatura)"
        or ATTRIBUTES["punti_ferita"] != "52 (7d8 + 21)"
        or ATTRIBUTES["velocita"] != "9 m"
    ):
        raise ValueError("independent_core_disagreement")
    return {
        "status": "eligible_status_only_source_review",
        "source_id": "erlw_2019_it",
        "registered_pages": [316],
        "original_attributes_unchanged": True,
        "numeric_gates_passed": True,
        "source_snapshot_unchanged": True,
        "separate_editorial_adjudication_required": True,
    }
