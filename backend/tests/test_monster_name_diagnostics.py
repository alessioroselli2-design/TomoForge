from services.monster_name_diagnostics import compact_name_boundary_match


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
