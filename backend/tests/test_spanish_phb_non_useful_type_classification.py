from __future__ import annotations

import hashlib
from pathlib import Path

from reference_library import CHARACTER_CREATION_REFERENCE_TYPES, REFERENCE_TYPES
from scripts.audit_bounded_native_text_parser_probe import bounded_native_text_parser_probe_windows


REPO_ROOT = Path(__file__).resolve().parents[2]
SPANISH_PHB = REPO_ROOT / "attached_assets" / "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
EXPECTED_SHA256 = "22987ea29717120c7b3ec4650017faa9fb0c0e9e7542be1357eda6b780ae71ad"
PROBE_WINDOWS = ((1, 3), (255, 257), (509, 511), (763, 765))


def test_spanish_phb_non_useful_named_types_are_classifiable_without_mutation() -> None:
    """Separate known non-character signal from parser fallback/unknown types."""
    assert SPANISH_PHB.is_file()
    assert hashlib.sha256(SPANISH_PHB.read_bytes()).hexdigest() == EXPECTED_SHA256

    result = bounded_native_text_parser_probe_windows(
        SPANISH_PHB,
        windows=PROBE_WINDOWS,
        source_language="es",
    )

    non_useful = result["non_useful_named_record_types_total"]
    known_reference_types = set(REFERENCE_TYPES)
    character_types = set(CHARACTER_CREATION_REFERENCE_TYPES)

    known_non_character = {
        reference_type: count
        for reference_type, count in non_useful.items()
        if reference_type in known_reference_types
        and reference_type not in character_types
        and reference_type != "other"
    }
    parser_fallback = int(non_useful.get("other", 0))
    unknown_types = {
        reference_type: count
        for reference_type, count in non_useful.items()
        if reference_type not in known_reference_types
    }

    # Every named non-useful signal must be explainable by the existing taxonomy
    # or the explicit parser fallback. Unknown emitted types would be a parser contract bug.
    assert unknown_types == {}
    assert (
        sum(known_non_character.values()) + parser_fallback
        == result["non_useful_named_records_detected_total"]
    )

    best_non_useful = result["best_window_non_useful_named_record_types"]
    best_unknown_types = {
        reference_type: count
        for reference_type, count in best_non_useful.items()
        if reference_type not in known_reference_types
    }
    assert best_unknown_types == {}

    # Keep the diagnostic inside the reviewed native-text-only budget and review gate.
    assert result["requested_pages_total"] == 12
    assert result["ocr_used"] is False
    assert result["translation_used"] is False
    assert result["external_processing_used"] is False
    assert result["database_read_used"] is False
    assert result["database_write_used"] is False
    assert result["records_persisted"] is False
    assert result["review_state_mutated"] is False
    assert result["canonicalization_performed"] is False
    assert result["automatic_import_authorized"] is False
