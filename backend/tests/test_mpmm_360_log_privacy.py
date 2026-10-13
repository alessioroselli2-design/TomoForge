"""Regression guard: historical MPMM OCR debugging must never log manual text."""

from pathlib import Path


def test_legacy_mpmm_debug_logging_excludes_manual_content():
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "repair_monsters_from_source.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        '"text": text[:5000]',
        '"identity_evidence":',
        '"title_evidence":',
        "MPMM_ADDOLORATO_AFFAMATO_DYNAMIC_TEXT",
        "MPMM_ADDOLORATO_SMARRITO_SPARSE_TEXT",
        "MPMM_ADDOLORATO_AFFAMATO_SPARSE_TEXT",
    )
    assert all(token not in script for token in forbidden)
    assert '"identity_evidence_count": 2' in script
    assert '"title_evidence_count": 1' in script
