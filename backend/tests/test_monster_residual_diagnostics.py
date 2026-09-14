from services.monster_residual_diagnostics import (
    residual_single_edit_agreement_counts,
    residual_single_edit_core_field_matches,
)


def test_residual_single_edit_core_field_matches_are_privacy_safe_and_fail_closed():
    left = {
        "classe_armatura": "14 armatura naturale",
        "punti_ferita": "37 (5d10+10)",
        "velocita": "12 m, volare 24 m",
    }
    right = {
        "classe_armatura": "14 armatura naturalf",
        "punti_ferita": "37 (5d10+1O)",
        "velocita": "12 m, volare 24 n",
    }

    result = residual_single_edit_core_field_matches(left, right)

    assert result == {
        "classe_armatura_residual_single_edit_match": True,
        "punti_ferita_residual_single_edit_match": True,
        "velocita_residual_single_edit_match": True,
    }
    serialized = str(result)
    assert "armatura" not in serialized
    assert "5d10" not in serialized
    assert "volare" not in serialized


def test_residual_single_edit_requires_semantic_agreement_and_deterministic_disagreement():
    exact = {
        "classe_armatura": "14",
        "punti_ferita": "37",
        "velocita": "12 m",
    }
    numeric_disagreement = {
        "classe_armatura": "13",
        "punti_ferita": "36",
        "velocita": "18 m",
    }

    assert residual_single_edit_core_field_matches(exact, exact) == {
        "classe_armatura_residual_single_edit_match": False,
        "punti_ferita_residual_single_edit_match": False,
        "velocita_residual_single_edit_match": False,
    }
    assert residual_single_edit_core_field_matches(exact, numeric_disagreement) == {
        "classe_armatura_residual_single_edit_match": False,
        "punti_ferita_residual_single_edit_match": False,
        "velocita_residual_single_edit_match": False,
    }


def test_residual_single_edit_counts_return_only_aggregate_numbers():
    primary = [
        {
            "start_page": 10,
            "normalized_name": "mostro prova",
            "attributes": {
                "classe_armatura": "14 armatura naturale",
                "punti_ferita": "37 (5d10+10)",
                "velocita": "12 m, volare 24 m",
            },
        }
    ]
    comparison = [
        {
            "start_page": 10,
            "normalized_name": "mostro prova",
            "attributes": {
                "classe_armatura": "14 armatura naturalf",
                "punti_ferita": "37 (5d10+1O)",
                "velocita": "12 m, volare 24 n",
            },
        }
    ]

    result = residual_single_edit_agreement_counts(primary, comparison)

    assert result == {
        "monster_primary_with_same_page_containment_and_deterministic_or_single_edit_core_match": 1,
        "monster_containment_classe_armatura_residual_single_edit_match": 1,
        "monster_containment_punti_ferita_residual_single_edit_match": 1,
        "monster_containment_velocita_residual_single_edit_match": 1,
        "monster_exact_key_classe_armatura_residual_single_edit_match": 1,
        "monster_exact_key_punti_ferita_residual_single_edit_match": 1,
        "monster_exact_key_velocita_residual_single_edit_match": 1,
    }
    assert all(isinstance(value, int) for value in result.values())
