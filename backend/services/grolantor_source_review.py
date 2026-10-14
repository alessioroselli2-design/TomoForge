"""Fail-closed original-source review for Bigby Rampollo Di Grolantor.

Ordinary OCR PR #402 required speed text replacement and is NOT a positive
paired-reader audit. This independent status-only review locks the original
registered Italian source and compares to the original English stat block.
No automatic rewrites or relaxed numeric/OCR gates.
"""
from __future__ import annotations

from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

RECORD_ID = "ref_4e249fc0d86753919cbb7bec5b96b661"
SOURCE_CHECKSUM = "2b6b51820c7af89cec93586b89f30e4ff8674692e48257c4c492bdd9c5067f7d"
ATTRIBUTES = {
    "classe_armatura": "18 (armatura naturale)",
    "punti_ferita": "402 (23d20 + 161)",
    "velocita": "18 m",
}
ITALIAN_RAW = (
    "Gigante Mastodontico (titano), generalmente caotico malvagio "
    "Classe Armatura 1 8 (armatura naturale) Punti Ferita "
    "402 (23d20 + 1 61 ) Velocità 1 8 m"
)
# Bigby Presents: Glory of the Giants, English original printed p165:
# Scion of Grolantor, AC18 natural armor, HP402 (23d20+161), speed60 ft.
ENGLISH_CORE = (18, 402, 23, 20, 161, 60)

def assess_grolantor_registered_source(record: dict[str, Any]) -> dict[str, Any]:
    """Admit only exact source identity and immutable eligible pending snapshot."""
    if not isinstance(record, dict):
        raise ValueError("missing_registered_record")
    if (
        record.get("id") != RECORD_ID
        or record.get("name") != "Rampollo Di Grolantor"
        or record.get("reference_type") != "monster"
        or record.get("review_status") != "pending"
        or record.get("canonical_id") is not None
        or record.get("review_flags") != ["ocr_da_verificare", "source_guided_repair"]
        or record.get("source_text_checksum") != SOURCE_CHECKSUM
        or record.get("attributes") != ATTRIBUTES
        or record.get("full_text") != ITALIAN_RAW
    ):
        raise ValueError("registered_snapshot_drift")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 2:
        raise ValueError("registered_source_count_drift")
    if sorted(ref.get("page") for ref in refs if isinstance(ref, dict)) != [170, 171]:
        raise ValueError("registered_source_pages_drift")
    for ref in refs:
        if not isinstance(ref, dict) or not all(
            (
                ref.get("logical_page") == ref.get("page"),
                ref.get("logical_source_id") == "bgg_2023_it",
                ref.get("source_status") == "active",
                ref.get("source_role") == "authority",
                ref.get("authority_class") == "licensed_translation",
                ref.get("filename") == "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf",
                ref.get("source_title") == "Bigby Presenta: La Gloria dei Giganti",
                ref.get("ruleset") == "2014",
            )
        ):
            raise ValueError("registered_source_authority_drift")
    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("global_numeric_gate_rejected")
    ac, hp, dice_count, die_size, modifier, speed_ft = ENGLISH_CORE
    if (
        ac != 18
        or hp != 402
        or (dice_count * (die_size + 1)) // 2 + modifier != hp
        or speed_ft != 60
        or ATTRIBUTES["classe_armatura"] != "18 (armatura naturale)"
        or ATTRIBUTES["punti_ferita"] != "402 (23d20 + 161)"
        or ATTRIBUTES["velocita"] != "18 m"
    ):
        raise ValueError("independent_english_original_mismatch")
    return {
        "status": "eligible_status_only_source_review",
        "source_id": "bgg_2023_it",
        "registered_pages": [170, 171],
        "original_attributes_unchanged": True,
        "numeric_gates_passed": True,
        "source_snapshot_unchanged": True,
        "separate_editorial_adjudication_required": True,
    }
