from __future__ import annotations

import hashlib
from pathlib import Path

from reference_library import CHARACTER_CREATION_REFERENCE_TYPES
from scripts.audit_bounded_native_text_parser_probe import bounded_native_text_parser_probe_windows


REPO_ROOT = Path(__file__).resolve().parents[2]
SPANISH_PHB = REPO_ROOT / "attached_assets" / "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
EXPECTED_SHA256 = "22987ea29717120c7b3ec4650017faa9fb0c0e9e7542be1357eda6b780ae71ad"


def test_spanish_phb_best_window_has_deterministic_dominant_reference_type() -> None:
    """Identify and expose the dominant typed signal without downstream mutation."""
    assert SPANISH_PHB.is_file()
    assert hashlib.sha256(SPANISH_PHB.read_bytes()).hexdigest() == EXPECTED_SHA256

    result = bounded_native_text_parser_probe_windows(
        SPANISH_PHB,
        windows=((1, 3), (255, 257), (509, 511), (763, 765)),
        source_language="es",
    )
    best = result["best_named_signal_window"]

    assert best is not None
    assert best["record_types"]

    ranked_types = sorted(
        best["record_types"].items(),
        key=lambda item: (-item[1], item[0]),
    )
    dominant_type, dominant_count = ranked_types[0]

    assert dominant_type
    assert dominant_count > 0
    assert dominant_count == max(best["record_types"].values())
    assert ranked_types == sorted(ranked_types, key=lambda item: (-item[1], item[0]))
    assert sum(best["record_types"].values()) == best["records_detected"]
    assert result["best_window_dominant_reference_type"] == dominant_type
    assert result["best_window_dominant_reference_type_count"] == dominant_count
    assert result["dominant_type_is_diagnostic_only"] is True

    # A Player's Handbook probe is only semantically promising when its strongest
    # named signal lands in the existing character-creation taxonomy rather than
    # the generic fallback bucket. This remains a diagnostic gate, not import approval.
    assert dominant_type in CHARACTER_CREATION_REFERENCE_TYPES
    assert dominant_type != "other"

    # Measure how much of the named signal in the strongest window belongs to the
    # useful character-creation taxonomy. Keep counts reconciled and diagnostic-only.
    assert sum(best["named_record_types"].values()) == best["named_records_detected"]
    useful_named_count = sum(
        count
        for reference_type, count in best["named_record_types"].items()
        if reference_type in CHARACTER_CREATION_REFERENCE_TYPES
    )
    assert useful_named_count > 0
    assert result["best_window_useful_named_records_detected"] == useful_named_count
    assert result["best_window_non_useful_named_records_detected"] == best["named_records_detected"] - useful_named_count
    assert result["best_window_useful_named_share"] == useful_named_count / best["named_records_detected"]
    assert 0 < result["best_window_useful_named_share"] <= 1
    assert result["useful_named_share_is_diagnostic_only"] is True

    assert sum(result["named_record_types_total"].values()) == result["named_records_detected_total"]
    assert (
        result["useful_named_records_detected_total"] + result["non_useful_named_records_detected_total"]
        == result["named_records_detected_total"]
    )

    # The diagnostic stays inside the previously reviewed 12-page native-text probe.
    assert result["requested_pages_total"] == 12
    assert result["best_window_selection_is_diagnostic_only"] is True
    assert result["ocr_used"] is False
    assert result["translation_used"] is False
    assert result["external_processing_used"] is False
    assert result["database_read_used"] is False
    assert result["database_write_used"] is False
    assert result["records_persisted"] is False
    assert result["review_state_mutated"] is False
    assert result["canonicalization_performed"] is False
    assert result["automatic_import_authorized"] is False
