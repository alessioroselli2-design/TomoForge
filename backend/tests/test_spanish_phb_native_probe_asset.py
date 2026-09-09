from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.audit_bounded_native_text_parser_probe import (
    bounded_native_text_parser_probe,
    bounded_native_text_parser_probe_windows,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPANISH_PHB = REPO_ROOT / "attached_assets" / "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
EXPECTED_SHA256 = "22987ea29717120c7b3ec4650017faa9fb0c0e9e7542be1357eda6b780ae71ad"


def test_spanish_phb_asset_matches_registry_and_has_native_text() -> None:
    """Exercise the real extraction aid without OCR, persistence, or translation."""
    assert SPANISH_PHB.is_file()
    assert hashlib.sha256(SPANISH_PHB.read_bytes()).hexdigest() == EXPECTED_SHA256

    result = bounded_native_text_parser_probe(
        SPANISH_PHB,
        start_page=1,
        end_page=12,
        source_language="es",
    )

    assert result["requested_pages"] == 12
    assert result["native_text_pages_available"] > 0
    assert result["bounded_native_text_parser_probe_executed"] is True
    assert result["ocr_callback_supplied"] is False
    assert result["ocr_used"] is False
    assert result["translation_used"] is False
    assert result["external_processing_used"] is False
    assert result["database_read_used"] is False
    assert result["database_write_used"] is False
    assert result["records_persisted"] is False
    assert result["review_state_mutated"] is False
    assert result["canonicalization_performed"] is False
    assert result["automatic_import_authorized"] is False


def test_spanish_phb_spread_probe_reports_structured_output_per_window() -> None:
    """Measure four tiny windows independently without authorizing an import."""
    result = bounded_native_text_parser_probe_windows(
        SPANISH_PHB,
        windows=((1, 3), (255, 257), (509, 511), (763, 765)),
        source_language="es",
    )

    assert result["window_count"] == 4
    assert result["requested_pages_total"] == 12
    assert result["records_detected_total"] > 0, result
    assert result["named_records_detected_total"] > 0, result
    assert result["named_records_detected_total"] + result["unnamed_records_detected_total"] == result["records_detected_total"]
    assert result["productive_windows"] >= result["named_signal_windows"] > 0, result
    assert result["productive_windows"] + result["empty_windows"] == result["window_count"]
    assert result["record_types_total"], result
    assert [(window["start_page"], window["end_page"]) for window in result["windows"]] == [
        (1, 3),
        (255, 257),
        (509, 511),
        (763, 765),
    ]
    assert all("records_detected" in window for window in result["windows"])
    assert all("named_records_detected" in window for window in result["windows"])
    assert all("unnamed_records_detected" in window for window in result["windows"])
    assert all("record_types" in window for window in result["windows"])
    assert all(window["ocr_used"] is False for window in result["windows"])
    assert result["ocr_used"] is False
    assert result["translation_used"] is False
    assert result["database_write_used"] is False
    assert result["records_persisted"] is False
    assert result["canonicalization_performed"] is False
    assert result["automatic_import_authorized"] is False
