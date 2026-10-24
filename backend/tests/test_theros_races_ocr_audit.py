"""Synthetic Theros source gates: no copied book text, no automatic verification."""

from scripts.theros_races_ocr_audit import FIRST, LAST, NAMES, facts


def test_expected_source_window_is_bounded_by_twelve_per_batch():
    assert (FIRST, LAST) == (19, 36)
    windows = [(s, min(s + 11, LAST)) for s in range(FIRST, LAST + 1, 12)]
    assert len(windows) == 2
    assert all(stop - start + 1 <= 12 for start, stop in windows)


def test_leonin_metadata_detects_traits_without_exporting_prose():
    sample = (
        "Leonin\nAbility Score Increase. An imaginary numerical example.\n"
        "Size. Medium playable character.\nSpeed. Thirty feet.\n"
        "Languages. Two imaginary languages.\nRoar. A fictional trait."
    )
    result = facts(sample)
    assert "Leonin" in result["possible_headings"]
    assert result["structural_markers"]["score_bonus"]
    assert result["structural_markers"]["size"]
    assert "imaginary" not in str(result)


def test_index_heading_alone_has_no_traits():
    result = facts("Leonin ........ 20\nSatyr ....... 24")
    assert result["structural_markers"]["score_bonus"] is False
    assert result["structural_markers"]["size"] is False


def test_only_the_five_theros_playable_nonhuman_races():
    assert set(NAMES) == {"Centaur", "Leonin", "Minotaur", "Satyr", "Triton"}
