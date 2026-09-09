from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.audit_bounded_native_text_parser_probe import bounded_native_text_parser_probe


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


def test_spanish_phb_spread_probe_detects_structured_parser_output() -> None:
    """Sample 12 total pages across the real aid and require actual parser output.

    The four windows are intentionally tiny and distributed through the 1,018-page
    physical asset. Each probe remains native-text-only and non-persistent; this
    test is only a readiness measurement, never an import authorization.
    """
    windows = ((1, 3), (255, 257), (509, 511), (763, 765))
    results = [
        bounded_native_text_parser_probe(
            SPANISH_PHB,
            start_page=start_page,
            end_page=end_page,
            source_language="es",
        )
        for start_page, end_page in windows
    ]

    assert sum(result["requested_pages"] for result in results) == 12
    assert all(result["ocr_used"] is False for result in results)
    assert all(result["translation_used"] is False for result in results)
    assert all(result["database_write_used"] is False for result in results)
    assert all(result["records_persisted"] is False for result in results)
    assert any(result["records_detected"] > 0 for result in results), results
