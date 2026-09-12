from services.monster_name_diagnostics import (
    compact_name_boundary_match,
    compact_name_single_edit_match,
)


def test_compact_name_boundary_match_accepts_only_word_boundary_noise():
    assert compact_name_boundary_match("private monster", "private mon ster") is True
    assert compact_name_boundary_match("private monster", "priv ate monster") is True


def test_compact_name_boundary_match_rejects_real_character_difference():
    assert compact_name_boundary_match("private monster", "private monater") is False


def test_compact_name_boundary_match_rejects_missing_word():
    assert compact_name_boundary_match("private elder monster", "private monster") is False


def test_compact_name_boundary_match_rejects_empty_names():
    assert compact_name_boundary_match("", "") is False
    assert compact_name_boundary_match("private monster", "") is False


def test_compact_name_boundary_match_returns_no_source_text():
    result = compact_name_boundary_match("private monster", "private mon ster")
    assert result is True
    assert isinstance(result, bool)


def test_compact_name_single_edit_match_accepts_one_substitution():
    assert compact_name_single_edit_match("private monster", "private monater") is True


def test_compact_name_single_edit_match_accepts_one_insertion_or_deletion():
    assert compact_name_single_edit_match("private monster", "private monsterr") is True
    assert compact_name_single_edit_match("private monster", "private monste") is True


def test_compact_name_single_edit_match_ignores_word_boundaries_before_distance():
    assert compact_name_single_edit_match("private monster", "private mon ater") is True


def test_compact_name_single_edit_match_rejects_exact_boundary_only_match():
    assert compact_name_single_edit_match("private monster", "private mon ster") is False


def test_compact_name_single_edit_match_rejects_larger_difference():
    assert compact_name_single_edit_match("private elder monster", "private monster") is False
    assert compact_name_single_edit_match("private monster", "public monster") is False


def test_compact_name_single_edit_match_rejects_empty_names_and_returns_bool():
    assert compact_name_single_edit_match("", "") is False
    result = compact_name_single_edit_match("private monster", "private monater")
    assert result is True
    assert isinstance(result, bool)
