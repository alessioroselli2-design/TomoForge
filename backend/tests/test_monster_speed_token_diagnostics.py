from scripts import pilot_local_ocr_parse_from_r2 as pilot
from services.monster_speed_token_diagnostics import (
    speed_extra_token_agreement_counts,
    speed_multi_extra_token_profile,
    speed_single_extra_token_profile,
)


def _attributes(speed: str) -> dict[str, str]:
    return {
        "classe_armatura": "14",
        "punti_ferita": "37",
        "velocita": speed,
    }


def test_speed_token_profile_classifies_internal_token_from_three_to_six_letters():
    result = speed_single_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("12 m abc rapido"),
    )

    assert result == {
        "velocita_residual_single_extra_alpha_token_len_3_to_6": True,
        "velocita_residual_single_extra_alpha_token_len_gt6": False,
        "velocita_residual_single_extra_alpha_token_internal": True,
    }
    assert "abc" not in str(result)
    assert "rapido" not in str(result)


def test_speed_token_profile_classifies_long_internal_token():
    result = speed_single_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("12 m lunghissimo rapido"),
    )

    assert result["velocita_residual_single_extra_alpha_token_len_3_to_6"] is False
    assert result["velocita_residual_single_extra_alpha_token_len_gt6"] is True
    assert result["velocita_residual_single_extra_alpha_token_internal"] is True


def test_speed_token_profile_does_not_call_edge_tokens_internal():
    prefix = speed_single_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("abc 12 m rapido"),
    )
    suffix = speed_single_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("12 m rapido abc"),
    )

    assert prefix["velocita_residual_single_extra_alpha_token_len_3_to_6"] is True
    assert suffix["velocita_residual_single_extra_alpha_token_len_3_to_6"] is True
    assert prefix["velocita_residual_single_extra_alpha_token_internal"] is False
    assert suffix["velocita_residual_single_extra_alpha_token_internal"] is False


def test_speed_token_profile_fails_closed_for_multiple_extras_or_numeric_change():
    multiple = speed_single_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("12 m abc def rapido"),
    )
    numeric_change = speed_single_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("13 m abc rapido"),
    )

    assert multiple
    assert numeric_change
    assert all(value is False for value in multiple.values())
    assert all(value is False for value in numeric_change.values())


def test_speed_multi_token_profile_distinguishes_exactly_two_from_three_or_more():
    exactly_two = speed_multi_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("12 m abc def rapido"),
    )
    three_or_more = speed_multi_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("12 m abc def ghi rapido"),
    )

    assert exactly_two == {
        "velocita_residual_extra_alpha_tokens_exactly_2": True,
        "velocita_residual_extra_alpha_tokens_3_or_more": False,
        "velocita_residual_duplicate_ambiguous": False,
    }
    assert three_or_more == {
        "velocita_residual_extra_alpha_tokens_exactly_2": False,
        "velocita_residual_extra_alpha_tokens_3_or_more": True,
        "velocita_residual_duplicate_ambiguous": False,
    }
    serialized = str(exactly_two) + str(three_or_more)
    for private_token in ("abc", "def", "ghi", "rapido"):
        assert private_token not in serialized


def test_speed_multi_token_profile_detects_duplicate_ambiguity_privately():
    result = speed_multi_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("12 m rapido rapido"),
    )

    assert result == {
        "velocita_residual_extra_alpha_tokens_exactly_2": False,
        "velocita_residual_extra_alpha_tokens_3_or_more": False,
        "velocita_residual_duplicate_ambiguous": True,
    }
    assert "rapido" not in str(result)


def test_speed_multi_token_profile_fails_closed_on_numeric_disagreement():
    result = speed_multi_extra_token_profile(
        _attributes("12 m rapido"),
        _attributes("13 m abc def rapido"),
    )

    assert all(value is False for value in result.values())


def test_speed_token_aggregate_counts_same_page_containment_only_and_stays_private():
    primary = [
        {
            "start_page": 10,
            "normalized_name": "mostro prova",
            "attributes": _attributes("12 m rapido"),
        }
    ]
    comparison = [
        {
            "start_page": 10,
            "normalized_name": "mostro prova alpha",
            "attributes": _attributes("12 m abc rapido"),
        },
        {
            "start_page": 11,
            "normalized_name": "mostro prova beta",
            "attributes": _attributes("12 m lunghissimo rapido"),
        },
    ]

    result = speed_extra_token_agreement_counts(primary, comparison)

    assert result == {
        "monster_containment_velocita_residual_single_extra_alpha_token_len_3_to_6": 1,
        "monster_containment_velocita_residual_single_extra_alpha_token_len_gt6": 0,
        "monster_containment_velocita_residual_single_extra_alpha_token_internal": 1,
        "monster_containment_velocita_residual_extra_alpha_tokens_exactly_2": 0,
        "monster_containment_velocita_residual_extra_alpha_tokens_3_or_more": 0,
        "monster_containment_velocita_residual_duplicate_ambiguous": 0,
    }
    assert all(isinstance(value, int) for value in result.values())
    serialized = str(result)
    assert "mostro prova" not in serialized
    assert "abc" not in serialized
    assert "lunghissimo" not in serialized
    assert "rapido" not in serialized


def test_speed_multi_token_aggregate_counts_all_three_new_signals_privately():
    primary = [
        {
            "start_page": 10,
            "normalized_name": "mostro prova",
            "attributes": _attributes("12 m rapido"),
        }
    ]
    comparison = [
        {
            "start_page": 10,
            "normalized_name": "mostro prova due",
            "attributes": _attributes("12 m abc def rapido"),
        },
        {
            "start_page": 10,
            "normalized_name": "mostro prova tre",
            "attributes": _attributes("12 m abc def ghi rapido"),
        },
        {
            "start_page": 10,
            "normalized_name": "mostro prova duplicato",
            "attributes": _attributes("12 m rapido rapido"),
        },
    ]

    result = speed_extra_token_agreement_counts(primary, comparison)

    assert result["monster_containment_velocita_residual_extra_alpha_tokens_exactly_2"] == 1
    assert result["monster_containment_velocita_residual_extra_alpha_tokens_3_or_more"] == 1
    assert result["monster_containment_velocita_residual_duplicate_ambiguous"] == 1
    assert all(isinstance(value, int) for value in result.values())
    serialized = str(result)
    for private_value in ("mostro prova", "abc", "def", "ghi", "rapido"):
        assert private_value not in serialized


def test_pilot_emits_speed_refinement_only_with_residual_diagnostics(monkeypatch):
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
    key = "monster_containment_velocita_residual_duplicate_ambiguous"

    monkeypatch.setattr(
        pilot,
        "speed_extra_token_agreement_counts",
        lambda primary, comparison: {key: 7},
    )

    default_summary = pilot._monster_parser_summary(
        [(12, text)],
        [(12, text)],
        "private-monster-manual.pdf",
        "it",
    )
    diagnostic_summary = pilot._monster_parser_summary(
        [(12, text)],
        [(12, text)],
        "private-monster-manual.pdf",
        "it",
        include_residual_single_edit=True,
    )

    assert key not in default_summary
    assert diagnostic_summary[key] == 7
