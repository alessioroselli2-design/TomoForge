from scripts.pilot_local_ocr_parse_from_r2 import _monster_parser_summary
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
        "punti_ferita": "37 (5d10+10)x",
        "velocita": "12 m, volare 24 n",
    }

    result = residual_single_edit_core_field_matches(left, right)

    assert result == {
        "classe_armatura_residual_single_edit_match": True,
        "punti_ferita_residual_single_edit_match": True,
        "velocita_residual_single_edit_match": True,
    }
    serialized = str(result)
    assert "naturale" not in serialized
    assert "5d10" not in serialized
    assert "volare" not in serialized


def test_residual_single_edit_rejects_every_numeric_signature_change():
    left = {
        "classe_armatura": "14 armatura naturale",
        "punti_ferita": "37 (5d10+10)",
        "velocita": "12 m, volare 24 m",
    }
    changed_numbers = {
        "classe_armatura": "15 armatura naturale",
        "punti_ferita": "37 (5d10+11)",
        "velocita": "12 m, volare 25 m",
    }

    assert residual_single_edit_core_field_matches(left, changed_numbers) == {
        "classe_armatura_residual_single_edit_match": False,
        "punti_ferita_residual_single_edit_match": False,
        "velocita_residual_single_edit_match": False,
    }


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
                "punti_ferita": "37 (5d10+10)x",
                "velocita": "12 m, volare 24 n",
            },
        }
    ]

    result = residual_single_edit_agreement_counts(primary, comparison)

    assert result == {
        "monster_primary_with_same_page_containment_and_deterministic_or_single_edit_core_match": 0,
        "monster_containment_classe_armatura_residual_single_edit_match": 0,
        "monster_containment_punti_ferita_residual_single_edit_match": 0,
        "monster_containment_velocita_residual_single_edit_match": 0,
        "monster_exact_key_classe_armatura_residual_single_edit_match": 1,
        "monster_exact_key_punti_ferita_residual_single_edit_match": 1,
        "monster_exact_key_velocita_residual_single_edit_match": 1,
    }
    assert all(isinstance(value, int) for value in result.values())
    serialized = str(result)
    assert "mostro prova" not in serialized
    assert "armatura naturale" not in serialized
    assert "5d10" not in serialized


def test_pilot_can_emit_residual_single_edit_counters_without_changing_default_summary():
    text = """LUPO TERRIBILE
Grande bestia, senza allineamento
Classe Armatura 14
Punti Ferita 37 (5d10+10)
Velocità 15 m
FOR DES COS INT SAG CAR
17 15 15 3 12 7
Sensi Percezione passiva 13
Linguaggi -
Grado di Sfida 1 (200 PE)
Azioni
Morso. Attacco con arma da mischia.
"""

    default_summary = _monster_parser_summary(
        [(12, text)],
        [(12, text)],
        "private-monster-manual.pdf",
        "it",
    )
    residual_summary = _monster_parser_summary(
        [(12, text)],
        [(12, text)],
        "private-monster-manual.pdf",
        "it",
        include_residual_single_edit=True,
    )

    key = "monster_exact_key_classe_armatura_residual_single_edit_match"
    assert key not in default_summary
    assert key in residual_summary
    assert residual_summary[key] == 0
    assert all(
        isinstance(value, int)
        for name, value in residual_summary.items()
        if "residual" in name or "single_edit_core" in name
    )
    serialized = str(residual_summary)
    assert "LUPO TERRIBILE" not in serialized
    assert "Morso" not in serialized
