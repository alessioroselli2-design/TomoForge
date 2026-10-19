"""Fail-closed review of original MM physical pp204–207."""
from copy import deepcopy

import pytest

from services import mm_manto_marinide_medusa_pages_204_207_review as mm


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
    ("name", "page", "hp", "gs"),
    [
        ("Manto Assassino", 204, "78 (12d10 + 12)", "8"),
        ("Mantoscuro", 205, "22 (5d6 + 5)", "1/2"),
        ("Marinide", 206, "11 (2d8 + 2)", "1/8"),
        ("Medusa", 207, "127 (17d8 + 51)", "6"),
    ],
)
def test_four_source_statblocks(name, page, hp, gs):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == gs
    assert result["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert result["writes"] == 0


def test_distinct_source_boxes_and_no_megera_pseudo_monster():
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 4
    assert all(mm.audit(n, catalog())["physical_page"] <= 207 for n in mm.MONSTERS)
    with pytest.raises(ValueError, match="not_a_source_statblock"):
        mm.audit("Congreghe di Megere", catalog())


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_duplicate_checks(name):
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit(name, catalog(), same_named_monster=True)


def test_registered_source_required():
    c = catalog()
    c["physical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Medusa", c)


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_tampered_original_stats_rejected(monkeypatch, name):
    data = deepcopy(mm.MONSTERS)
    data[name]["ac"] = "99"
    monkeypatch.setattr(mm, "MONSTERS", data)
    with pytest.raises(ValueError, match="original_source_fields_changed"):
        mm.audit(name, catalog())


def test_defensive_attrs_copy():
    first = mm.audit("Mantoscuro", catalog())
    first["attributes"]["caratteristiche"]["int"] = "30"
    assert mm.audit("Mantoscuro", catalog())[
        "attributes"
    ]["caratteristiche"]["int"] == "2"
