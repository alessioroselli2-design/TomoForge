from services.monster_residual_diagnostics import (
    residual_shape_agreement_counts,
    residual_shape_core_field_matches,
)


def test_single_extra_token_profile_classifies_short_prefix_and_suffix_privately():
    left = {
        "classe_armatura": "14",
        "punti_ferita": "37 (5d10+10) robusto",
        "velocita": "12 m volare rapido",
    }
    right = {
        "classe_armatura": "14",
        "punti_ferita": "x 37 (5d10+10) robusto",
        "velocita": "12 m volare rapido zz",
    }

    result = residual_shape_core_field_matches(left, right)

    assert result["punti_ferita_residual_single_extra_alpha_token_short_lt3"] is True
    assert result["punti_ferita_residual_single_extra_alpha_token_prefix"] is True
    assert result["punti_ferita_residual_single_extra_alpha_token_suffix"] is False
    assert result["velocita_residual_single_extra_alpha_token_short_lt3"] is True
    assert result["velocita_residual_single_extra_alpha_token_prefix"] is False
    assert result["velocita_residual_single_extra_alpha_token_suffix"] is True

    serialized = str(result)
    assert "robusto" not in serialized
    assert "volare" not in serialized
    assert "zz" not in serialized


def test_single_extra_token_short_signal_rejects_three_or_more_letters():
    left = {
        "classe_armatura": "14",
        "punti_ferita": "37 robusto",
        "velocita": "12 m",
    }
    right = {
        "classe_armatura": "14",
        "punti_ferita": "abc 37 robusto",
        "velocita": "12 m xyz",
    }

    result = residual_shape_core_field_matches(left, right)

    assert result["punti_ferita_residual_single_extra_alpha_token_short_lt3"] is False
    assert result["punti_ferita_residual_single_extra_alpha_token_prefix"] is True
    assert result["velocita_residual_single_extra_alpha_token_short_lt3"] is False
    assert result["velocita_residual_single_extra_alpha_token_suffix"] is True


def test_single_extra_token_profile_fails_closed_for_multiple_or_ambiguous_extras():
    left = {
        "classe_armatura": "14",
        "punti_ferita": "37 robusto",
        "velocita": "12 m rapido",
    }
    right = {
        "classe_armatura": "14",
        "punti_ferita": "x y 37 robusto",
        "velocita": "x 12 m rapido x",
    }

    result = residual_shape_core_field_matches(left, right)

    for field in ("punti_ferita", "velocita"):
        assert result[f"{field}_residual_single_extra_alpha_token_short_lt3"] is False
        assert result[f"{field}_residual_single_extra_alpha_token_prefix"] is False
        assert result[f"{field}_residual_single_extra_alpha_token_suffix"] is False


def test_single_extra_token_profile_fails_closed_on_numeric_disagreement():
    left = {
        "classe_armatura": "14",
        "punti_ferita": "37 robusto",
        "velocita": "12 m rapido",
    }
    right = {
        "classe_armatura": "14",
        "punti_ferita": "x 38 robusto",
        "velocita": "13 m rapido zz",
    }

    result = residual_shape_core_field_matches(left, right)

    for field in ("punti_ferita", "velocita"):
        assert result[f"{field}_residual_single_extra_alpha_token_short_lt3"] is False
        assert result[f"{field}_residual_single_extra_alpha_token_prefix"] is False
        assert result[f"{field}_residual_single_extra_alpha_token_suffix"] is False


def test_aggregate_position_and_length_counters_return_only_integers():
    primary = [
        {
            "start_page": 10,
            "normalized_name": "mostro prova",
            "attributes": {
                "classe_armatura": "14",
                "punti_ferita": "37 (5d10+10) robusto",
                "velocita": "12 m volare rapido",
            },
        }
    ]
    comparison = [
        {
            "start_page": 10,
            "normalized_name": "mostro prova alpha",
            "attributes": {
                "classe_armatura": "14",
                "punti_ferita": "x 37 (5d10+10) robusto",
                "velocita": "12 m volare rapido zz",
            },
        }
    ]

    result = residual_shape_agreement_counts(primary, comparison)

    assert result["monster_containment_punti_ferita_residual_single_extra_alpha_token_short_lt3"] == 1
    assert result["monster_containment_punti_ferita_residual_single_extra_alpha_token_prefix"] == 1
    assert result["monster_containment_punti_ferita_residual_single_extra_alpha_token_suffix"] == 0
    assert result["monster_containment_velocita_residual_single_extra_alpha_token_short_lt3"] == 1
    assert result["monster_containment_velocita_residual_single_extra_alpha_token_prefix"] == 0
    assert result["monster_containment_velocita_residual_single_extra_alpha_token_suffix"] == 1
    assert all(isinstance(value, int) for value in result.values())

    serialized = str(result)
    assert "mostro prova" not in serialized
    assert "robusto" not in serialized
    assert "volare" not in serialized
    assert "zz" not in serialized
