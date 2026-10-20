"""Monster speed metric display regression, without rewriting source imports."""

from copy import deepcopy

import pytest

from reference_library import metric_monster_speed, reference_to_card_payload


@pytest.mark.parametrize(
    ("original", "metric"),
    [
        ("30 ft.", "9 m"),
        ("40 ft.", "12 m"),
        ("5 ft.", "1,5 m"),
        ("25 ft.", "7,5 m"),
        ("35 ft.", "10,5 m"),
        ("0 ft.", "0 m"),
        ("60 ft.", "18 m"),
        ("30 ft., swim 30 ft.", "9 m, nuotare 9 m"),
        ("40 ft., climb 20 ft., burrow 10 ft.", "12 m, scalare 6 m, scavare 3 m"),
        ("0 ft., fly 60 ft. (hover)", "0 m, volare 18 m (fluttuare)"),
        ("30 ft., fly 30 ft. (hover), swim 30 ft.", "9 m, volare 9 m (fluttuare), nuotare 9 m"),
        ("9 m", "9 m"),
        ("12 metri, volare 18 m", "12 metri, volare 18 m"),
        # Unknown or non-standard feet distances are never approximated.
        ("7 ft.", "7 ft."),
        ("30 ft., fly 7 ft.", "30 ft., fly 7 ft."),
        ("speed unknown", "speed unknown"),
        ("30 feet", "9 m"),
    ],
)
def test_game_metric_speed_conversion(original, metric):
    assert metric_monster_speed(original) == metric


def test_metric_conversion_does_not_modify_db_source_or_nested_abilities():
    source = {
        "velocita": "30 ft.",
        "classe_armatura": "12 (natural armor)",
        "punti_ferita": "19 (3d8 + 6)",
        "grado_sfida": "1/2",
        "caratteristiche": {
            "for": 10, "des": 11, "cos": 14, "int": 6, "sag": 8, "car": 3,
        },
    }
    monster = {
        "id": "creeper",
        "reference_type": "monster",
        "name": "Creeper",
        "source_name": "Creeper",
        "review_status": "verified",
        "source_language": "en",
        "attributes": deepcopy(source),
        "source_attributes": deepcopy(source),
        "source_refs": [{"filename": "manual.pdf", "page": 30}],
    }
    original = deepcopy(monster)
    payload = reference_to_card_payload(monster)
    assert payload["attributes"]["velocita"] == "9 m"
    assert payload["attributes"]["punti_ferita"] == "19 (3d8 + 6)"
    assert payload["attributes"]["classe_armatura"] == "12 (natural armor)"
    assert [payload["attributes"][key] for key in (
        "for", "des", "cos", "int", "sag", "car"
    )] == [10, 11, 14, 6, 8, 3]
    assert monster == original


def test_already_italian_speed_does_not_change():
    monster = {
        "id": "creeper",
        "reference_type": "monster",
        "name": "Creeper",
        "attributes": {"velocita": "9 m"},
        "source_attributes": {"velocita": "30 ft."},
    }
    assert reference_to_card_payload(monster)["attributes"]["velocita"] == "9 m"
    assert monster["source_attributes"]["velocita"] == "30 ft."


def test_non_monster_references_are_not_converted():
    race = {
        "id": "race",
        "reference_type": "race",
        "name": "Raza",
        "attributes": {"velocita": "30 ft."},
    }
    assert reference_to_card_payload(race)["attributes"]["velocita"] == "30 ft."
