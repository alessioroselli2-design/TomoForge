"""Read-only source and negative-regression tests for MM pp200–203."""
from copy import deepcopy

import pytest

from services import mm_magmin_maligni_manticora_pages_200_203_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256,
        "physical_pages": mm.PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(
    ("name", "page", "hp", "cr"),
    [
        ("Magmin", 200, "9 (2d6 + 2)", "1/2"),
        ("Ago Maligno", 202, "11 (2d8 + 2)", "1/4"),
        ("Arbusto Maligno", 202, "4 (1d6 + 1)", "1/8"),
        ("Rampicante Maligno", 202, "26 (4d8 + 8)", "1/2"),
        ("Manticora", 203, "68 (8d10 + 24)", "3"),
    ],
)
def test_core_statistics_from_original(name, page, hp, cr):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == cr
    assert result["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert result["writes"] == 0


def test_three_independent_boxes_on_p202():
    blocks = [mm.audit(name, catalog()) for name in (
        "Ago Maligno", "Arbusto Maligno", "Rampicante Maligno",
    )]
    assert {b["physical_page"] for b in blocks} == {202}
    assert len({b["id"] for b in blocks}) == 3


def test_p201_lore_never_becomes_a_monster():
    assert all(mm.audit(n, catalog())["physical_page"] != 201 for n in mm.MONSTERS)
    with pytest.raises(ValueError, match="not_an_independent_source_statblock"):
        mm.audit("Maligno", catalog())


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_collision_rejected(name):
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit(name, catalog(), same_named_monster=True)


def test_source_authority_required():
    for key, bad in (
        ("physical_sha256", "0" * 64),
        ("source_status", "superseded"),
        ("physical_pages", 354),
    ):
        c = catalog()
        c[key] = bad
        with pytest.raises(ValueError, match="original_source_mismatch"):
            mm.audit("Magmin", c)


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_changed_source_stats_rejected(monkeypatch, name):
    data = deepcopy(mm.MONSTERS)
    data[name]["hp"] = "999 (1d6 + 1)"
    monkeypatch.setattr(mm, "MONSTERS", data)
    with pytest.raises(ValueError, match="original_source_fields_changed"):
        mm.audit(name, catalog())


def test_defensive_result_copy():
    first = mm.audit("Manticora", catalog())
    first["attributes"]["caratteristiche"]["for"] = "30"
    assert mm.audit("Manticora", catalog())[
        "attributes"
    ]["caratteristiche"]["for"] == "17"
