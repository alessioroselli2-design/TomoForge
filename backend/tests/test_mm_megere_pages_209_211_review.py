"""Negative and source-specific regression tests for Monster Manual pp209-211."""
from copy import deepcopy
import pytest
from services import mm_megere_pages_209_211_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID, "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256, "physical_pages": mm.PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }


@pytest.mark.parametrize("name,page,hp,gs,coven", [
    ("Megera Marina", 209, "52 (7d8 + 21)", "2", "4"),
    ("Megera Notturna", 210, "112 (15d8 + 45)", "5", "7"),
    ("Megera Verde", 211, "82 (11d8 + 33)", "3", "5"),
])
def test_source_statblock_and_distinct_coven_variant(name, page, hp, gs, coven):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["grado_sfida_in_congrega"] == coven
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_only_three_statblocks_not_congreghe_or_lore():
    assert len(mm.MONSTERS) == 3
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 3
    with pytest.raises(ValueError, match="not_a_source_statblock"):
        mm.audit("Congrega di Megere", catalog())


@pytest.mark.parametrize("badfield,value", [
    ("physical_sha256", "other"), ("physical_pages", 352),
    ("source_status", "inactive"), ("text_mode", "ocr_only"),
    ("logical_source_id", "other"),
])
def test_wrong_authority_fails_closed(badfield, value):
    c = catalog()
    c[badfield] = value
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Megera Verde", c)


def test_duplicate_rejected_and_data_mutations_detected():
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Megera Verde", catalog(), same_named_monster=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Megera Verde", catalog(), existing_id=True)
    original = deepcopy(mm.MONSTERS["Megera Marina"])
    try:
        mm.MONSTERS["Megera Marina"]["hp"] = "53 (7d8 + 21)"
        with pytest.raises(ValueError, match="original_source_fields_changed"):
            mm.audit("Megera Marina", catalog())
    finally:
        mm.MONSTERS["Megera Marina"] = original


def test_defensive_attributes_copy():
    first = mm.audit("Megera Notturna", catalog())
    first["attributes"]["caratteristiche"]["for"] = "-99"
    second = mm.audit("Megera Notturna", catalog())
    assert second["attributes"]["caratteristiche"]["for"] == "18"
