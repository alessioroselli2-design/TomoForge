"""Original Italian MM pp257-264 numeric/identity and failure-mode tests."""
from copy import deepcopy
import pytest
from services import mm_rakshasa_sahuagin_pages_257_264_review as mm


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
    ("Rakshasa", 257, "110 (13d8 + 52)", "13"),
    ("Remorhaz Giovane", 258, "93 (11d10 + 33)", "5"),
    ("Remorhaz", 258, "195 (17d12 + 85)", "11"),
    ("Revenant", 259, "136 (16d8 + 64)", "5"),
    ("Roc", 260, "248 (16d20 + 80)", "11"),
    ("Rugginofago", 261, "27 (5d8 + 5)", "1/2"),
    ("Sahuagin", 262, "22 (4d8 + 4)", "1/2"),
    ("Sahuagin Sacerdotessa", 263, "33 (6d8 + 6)", "2"),
    ("Sahuagin Barone", 263, "76 (9d10 + 27)", "5"),
    ("Serpente di Fuoco", 264, "22 (5d8)", "1"),
])
def test_ten_independent_source_boxes(name, page, hp, gs):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == gs
    assert result["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert result["writes"] == 0


def test_shared_pages_have_independent_statblocks():
    assert len(mm.MONSTERS) == 10
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 10
    assert mm.audit("Remorhaz", catalog())["physical_page"] == 258
    assert mm.audit("Remorhaz Giovane", catalog())["physical_page"] == 258
    assert mm.audit("Sahuagin Sacerdotessa", catalog())["physical_page"] == 263
    assert mm.audit("Sahuagin Barone", catalog())["physical_page"] == 263


def test_no_pseudo_monsters_and_fail_closed():
    with pytest.raises(ValueError, match="not_an_original_statblock"):
        mm.audit("Sahuagin Sacerdotessa Incantesimi", catalog())
    bad = catalog()
    bad["physical_sha256"] = "tampered"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Roc", bad)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Roc", catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Roc", catalog(), same_named_monster=True)


def test_mutation_and_copy_isolation():
    old = deepcopy(mm.MONSTERS["Rugginofago"])
    try:
        mm.MONSTERS["Rugginofago"]["hp"] = "30 (5d8 + 5)"
        with pytest.raises(ValueError, match="original_source_fields_changed"):
            mm.audit("Rugginofago", catalog())
    finally:
        mm.MONSTERS["Rugginofago"] = old
    record = mm.audit("Sahuagin", catalog())
    record["attributes"]["caratteristiche"]["for"] = "99"
    assert mm.audit("Sahuagin", catalog())["attributes"]["caratteristiche"]["for"] == "13"
