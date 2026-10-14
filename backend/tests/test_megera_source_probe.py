"""The probe never returns any source text and uses stable positioning."""

from types import SimpleNamespace

from services.megera_source_probe import compact_word, page_safe_geometry


def test_unicode_normalization_and_punctuation():
    assert compact_word("Velocità:") == "velocita"
    assert compact_word("15d8") == "15d8"
    assert compact_word("MÈGERA") == "megera"


def test_privacy_safe_line_metadata_only():
    words = [
        (10, 15, 40, 20, "Megera", 0, 0, 0),
        (42, 15, 82, 20, "Crepuscolare", 0, 0, 1),
        (10, 30, 42, 38, "Classe", 0, 1, 0),
        (45, 30, 83, 38, "Armatura", 0, 1, 1),
        (88, 30, 94, 38, "17", 0, 1, 2),
        (10, 50, 24, 57, "Punti", 0, 2, 0),
        (28, 50, 46, 57, "Ferita", 0, 2, 1),
        (50, 50, 58, 57, "82", 0, 2, 2),
    ]
    page = SimpleNamespace(
        get_text=lambda mode, sort=False: words,
        rect=SimpleNamespace(width=100, height=100),
    )
    result = page_safe_geometry(page, 305)
    assert result["title_lines"] == 1
    assert result["ca_labels"] == 1
    assert result["hp_labels"] == 1
    assert result["lines"][1]["has_17"]
    assert result["lines"][2]["has_82"]
    assert "Megera" not in str(result)
    assert "Ferita" not in str(result)
