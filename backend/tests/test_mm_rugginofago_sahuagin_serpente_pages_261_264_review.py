"""Italian original Monster Manual p261–264: five physical statblocks."""
from copy import deepcopy
import pytest
from services import mm_rugginofago_sahuagin_serpente_pages_261_264_review as mm


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


@pytest.mark.parametrize("name,page,hp,gs", [
    ("Rugginofago", 261, "27 (5d8 + 5)", "1/2"),
    ("Sahuagin", 262, "22 (4d8 + 4)", "1/2"),
    ("Sahuagin Sacerdotessa", 263, "33 (6d8 + 6)", "2"),
    ("Sahuagin Barone", 263, "76 (9d10 + 27)", "5"),
    ("Serpente di Fuoco", 264, "22 (5d8)", "1"),
])
def test_original_source(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_three_different_sahuagin_and_fire_serpent_not_salamandra():
    assert len(mm.MONSTERS) == 5
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 5
    assert mm.audit("Sahuagin Barone", catalog())["physical_page"] == 263
    assert mm.audit("Sahuagin Sacerdotessa", catalog())["physical_page"] == 263
    with pytest.raises(ValueError, match="not_an_original_statblock"):
        mm.audit("Salamandra", catalog())


def test_source_wrong_collision_and_mutation():
    c = catalog()
    c["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Serpente di Fuoco", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Sahuagin", catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Sahuagin", catalog(), same_named_monster=True)
    saved = deepcopy(mm.MONSTERS["Rugginofago"])
    try:
        mm.MONSTERS["Rugginofago"]["hp"] = "28 (5d8 + 5)"
        with pytest.raises(ValueError, match="source_fields_changed"):
            mm.audit("Rugginofago", catalog())
    finally:
        mm.MONSTERS["Rugginofago"] = saved


def test_returned_attributes_are_defensive_copy():
    r = mm.audit("Sahuagin Barone", catalog())
    r["attributes"]["azioni_nomi_da_completare"].clear()
    assert mm.audit("Sahuagin Barone", catalog())["attributes"]["azioni_nomi_da_completare"]
