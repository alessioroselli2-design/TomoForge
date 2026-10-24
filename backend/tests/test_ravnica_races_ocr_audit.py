"""Race heading detection is metadata-only and cannot approve a PDF."""

from scripts.ravnica_races_ocr_audit import FIRST, LAST, NAMES, facts


def test_single_twelve_page_window():
    assert (FIRST, LAST) == (12, 23)
    assert LAST - FIRST + 1 == 12


def test_detect_loxodon_statistical_section_without_prose_leakage():
    text = (
        "Loxodon\n"
        "Ability Score Increase. Sample ability rule.\n"
        "Size. The sample playable size is printed here.\n"
        "Speed. A walking speed is printed here.\n"
        "Languages. Known languages are listed."
    )
    out = facts(text)
    assert "Loxodon" in out["possible_headings"]
    assert out["structural_markers"]["score_bonus"]
    assert out["structural_markers"]["size"]
    assert out["structural_markers"]["speed"]
    assert text not in str(out)


def test_index_mentions_are_not_sufficient_to_confirm_full_race():
    out = facts("Loxodon . . . . 17\nSimic Hybrid . . . . 20")
    assert not out["structural_markers"]["score_bonus"]
    assert not out["structural_markers"]["size"]


def test_whitelist_has_no_unrelated_races():
    assert set(NAMES) == {
        "Centaur", "Goblin", "Loxodon", "Minotaur", "Simic Hybrid", "Vedalken"
    }
