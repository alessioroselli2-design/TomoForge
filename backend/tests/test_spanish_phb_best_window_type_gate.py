from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.audit_bounded_native_text_parser_probe import bounded_native_text_parser_probe_windows


REPO_ROOT = Path(__file__).resolve().parents[2]
SPANISH_PHB = REPO_ROOT / "attached_assets" / "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
EXPECTED_SHA256 = "22987ea29717120c7b3ec4650017faa9fb0c0e9e7542be1357eda6b780ae71ad"


def test_spanish_phb_best_window_has_coherent_typed_named_signal() -> None:
    """Require the best bounded window to expose a coherent typed signal only."""
    assert SPANISH_PHB.is_file()
    assert hashlib.sha256(SPANISH_PHB.read_bytes()).hexdigest() == EXPECTED_SHA256

    result = bounded_native_text_parser_probe_windows(
        SPANISH_PHB,
        windows=((1, 3), (255, 257), (509, 511), (763, 765)),
        source_language="es",
    )
    best = result["best_named_signal_window"]

    assert best is not None
    assert best["named_records_detected"] > 0
    assert best["record_types"]
    assert sum(best["record_types"].values()) == best["records_detected"]
    assert max(best["record_types"].values()) > 0

    assert result["requested_pages_total"] == 12
    assert result["best_window_selection_is_diagnostic_only"] is True
    assert result["ocr_used"] is False
    assert result["translation_used"] is False
    assert result["database_write_used"] is False
    assert result["records_persisted"] is False
    assert result["canonicalization_performed"] is False
    assert result["automatic_import_authorized"] is False
