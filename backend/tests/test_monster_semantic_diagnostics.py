from services.monster_semantic_diagnostics import (
    deterministic_core_field_matches,
    semantic_core_field_matches,
)


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


def test_deterministic_core_normalization_handles_only_presentation_noise():
    left = {
        "classe_armatura": "14 (armatura naturale)",
        "punti_ferita": "37 (5d10+10)",
        "velocita": "12 m, volare 24 m",
    }
    right = {
        "classe_armatura": "CA: 14 armatura naturale",
        "punti_ferita": "PF 37; 5 d 10 + 10",
        "velocita": "Velocità: 12 metri / volare 24 metri",
    }

    result = deterministic_core_field_matches(left, right)

    assert result == {
        "classe_armatura_deterministic_match": True,
        "punti_ferita_deterministic_match": True,
        "velocita_deterministic_match": True,
    }
    serialized = str(result)
    assert "armatura naturale" not in serialized
    assert "5d10" not in serialized
    assert "volare" not in serialized


def test_deterministic_core_normalization_preserves_unknown_text_and_disagreements():
    left = {
        "classe_armatura": "14 armatura naturale",
        "punti_ferita": "37 (5d10+10)",
        "velocita": "12 m, volare 24 m",
    }
    right = {
        "classe_armatura": "14 scudo",
        "punti_ferita": "37 formula OCR differente",
        "velocita": "12 m, nuoto 24 m",
    }

    assert deterministic_core_field_matches(left, right) == {
        "classe_armatura_deterministic_match": False,
        "punti_ferita_deterministic_match": False,
        "velocita_deterministic_match": False,
    }


def test_deterministic_core_normalization_does_not_strip_prefix_inside_unknown_text():
    left = {
        "classe_armatura": "CAfoo 14",
        "punti_ferita": "PFbar 37",
        "velocita": "VELbaz 12 m",
    }
    right = {
        "classe_armatura": "foo 14",
        "punti_ferita": "bar 37",
        "velocita": "baz 12 m",
    }

    assert deterministic_core_field_matches(left, right) == {
        "classe_armatura_deterministic_match": False,
        "punti_ferita_deterministic_match": False,
        "velocita_deterministic_match": False,
    }


def test_deterministic_core_normalization_fails_closed_without_numeric_content():
    empty = {
        "classe_armatura": "CA sconosciuta",
        "punti_ferita": "PF ?",
        "velocita": "Velocità --",
    }

    assert deterministic_core_field_matches(empty, empty) == {
        "classe_armatura_deterministic_match": False,
        "punti_ferita_deterministic_match": False,
        "velocita_deterministic_match": False,
    }
