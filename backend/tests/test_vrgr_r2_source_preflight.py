"""No canonical writes or disclosure from Van Richten source preflight."""
from pathlib import Path

import pytest
from scripts import vrgr_r2_source_preflight as p


def test_signals_native_structure_only():
    text = (
        "Mostro\\nClasse Armatura 13\\nPunti Ferita 45 (6d8 + 18)\\n"
        "Velocità 9 m\\nFOR DES COS INT SAG CAR\\n"
    )
    flags = p.native_page_signals(text)
    assert flags["monster_like_page"] is True
    assert flags["structural_markers"] == 3
    assert flags["ability_labels"] == 6
    assert p.WRITES == 0


def test_partial_page_cannot_pass_as_statblock():
    flags = p.native_page_signals("Classe Armatura 12\\nPunti Ferita 5")
    assert flags["monster_like_page"] is False
    assert flags["ability_labels"] == 0


def test_non_source_pdf_fails_before_any_parsing(tmp_path: Path):
    untrusted = tmp_path / "fake.pdf"
    untrusted.write_bytes(b"%PDF-1.4\\nnot registered source")
    with pytest.raises(ValueError, match="registered_original_sha256_mismatch"):
        p.inspect_local_pdf(untrusted)
