from services.monster_semantic_diagnostics import semantic_core_field_matches


def test_semantic_core_matches_ignore_accessory_ocr_text_without_exposing_values():
    left = {
        "classe_armatura": "14 (armatura naturale)",
        "punti_ferita": "37 (5d10+10)",
        "velocita": "12 m, volare 24 m",
    }
    right = {
        "classe_armatura": "14 armatura naturale",
        "punti_ferita": "37 5d10 + 10",
        "velocita": "12 metri; volare 24 metri",
    }

    result = semantic_core_field_matches(left, right)

    assert result == {
        "classe_armatura_semantic_match": True,
        "punti_ferita_semantic_match": True,
        "velocita_semantic_match": True,
    }
    serialized = str(result)
    assert "armatura naturale" not in serialized
    assert "5d10" not in serialized
    assert "volare" not in serialized


def test_semantic_core_matches_detect_real_numeric_disagreement():
    left = {
        "classe_armatura": "14",
        "punti_ferita": "37 (5d10+10)",
        "velocita": "12 m, volare 24 m",
    }
    right = {
        "classe_armatura": "13",
        "punti_ferita": "36 (5d10+9)",
        "velocita": "12 m, volare 18 m",
    }

    assert semantic_core_field_matches(left, right) == {
        "classe_armatura_semantic_match": False,
        "punti_ferita_semantic_match": False,
        "velocita_semantic_match": False,
    }


def test_semantic_core_matches_do_not_treat_missing_values_as_equal():
    empty = {
        "classe_armatura": "",
        "punti_ferita": None,
        "velocita": "unknown",
    }

    assert semantic_core_field_matches(empty, empty) == {
        "classe_armatura_semantic_match": False,
        "punti_ferita_semantic_match": False,
        "velocita_semantic_match": False,
    }
