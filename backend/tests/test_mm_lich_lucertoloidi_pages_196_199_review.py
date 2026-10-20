"""Fail-closed original-source checks for MM p196–199."""
from copy import deepcopy

import pytest

from services import mm_lich_lucertoloidi_pages_196_199_review as mm


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
        ("Lich", 196, "135 (18d8 + 54)", "21"),
        ("Lucertoloide", 198, "22 (4d8 + 4)", "1/2"),
        ("Lucertoloide Sciamano", 199, "27 (5d8 + 5)", "2"),
        ("Re/Regina Lucertola", 199, "78 (12d8 + 24)", "4"),
    ],
)
def test_original_statblocks(name, page, hp, cr):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == cr
    assert result["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert result["writes"] == 0


def test_page_197_is_lore_not_an_extra_statblock():
    assert 197 not in [mm.audit(n, catalog())["physical_page"] for n in mm.MONSTERS]
    with pytest.raises(ValueError, match="not_a_source_statblock"):
        mm.audit("Lich - Tana", catalog())


def test_page_199_has_two_distinct_statblocks_and_shared_king_queen_box():
    shaman = mm.audit("Lucertoloide Sciamano", catalog())
    ruler = mm.audit("Re/Regina Lucertola", catalog())
    assert shaman["physical_page"] == ruler["physical_page"] == 199
    assert shaman["id"] != ruler["id"]
    assert "Re Lucertola" not in mm.MONSTERS
    assert "Regina Lucertola" not in mm.MONSTERS


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_collision_rejected(name):
    for kwargs in ({"existing_id": True}, {"same_named_monster": True}):
        with pytest.raises(ValueError, match="monster_collision"):
            mm.audit(name, catalog(), **kwargs)


def test_non_monster_race_name_elsewhere_not_auto_blocked():
    # The database contains a separate "Lucertoloide" race-related 'other'
    # record in MPMM; this check is only for MONSTER name collisions.
    result = mm.audit("Lucertoloide", catalog(), same_named_monster=False)
    assert result["writes"] == 0


def test_invalid_catalog_rejected():
    for key, changed in (
        ("physical_sha256", "0" * 64),
        ("physical_pages", 352),
        ("source_status", "superseded"),
    ):
        c = catalog()
        c[key] = changed
        with pytest.raises(ValueError, match="original_source_mismatch"):
            mm.audit("Lich", c)


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_mutated_source_fields_fail_closed(monkeypatch, name):
    changed = deepcopy(mm.MONSTERS)
    changed[name]["scores"][0] = 30
    monkeypatch.setattr(mm, "MONSTERS", changed)
    with pytest.raises(ValueError, match="original_source_fields_changed"):
        mm.audit(name, catalog())


def test_mutated_result_does_not_change_source():
    first = mm.audit("Lucertoloide Sciamano", catalog())
    first["attributes"]["caratteristiche"]["for"] = "30"
    assert mm.audit("Lucertoloide Sciamano", catalog())[
        "attributes"
    ]["caratteristiche"]["for"] == "15"


def test_legendaries_not_promoted_to_full_text():
    attrs = mm.audit("Lich", catalog())["attributes"]
    assert attrs["azioni_leggendarie_nomi_da_completare"] == [
        "Trucchetto", "Tocco Paralizzante", "Sguardo Terrificante",
        "Distruggere Vita",
    ]
    assert "azioni" not in attrs
