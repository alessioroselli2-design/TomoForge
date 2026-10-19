"""Fail-closed Italian MM p273-280 individual original-source stats checks."""
from copy import deepcopy
import pytest
from services import mm_ginosfinge_slaad_spettri_pages_273_280_review as mm


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
    ("Ginosfinge", 273, "136 (16d10 + 48)", "11"),
    ("Slaad Girino", 276, "10 (4d4)", "1/8"),
    ("Slaad Rosso", 276, "93 (11d10 + 33)", "5"),
    ("Slaad Blu", 276, "123 (13d10 + 52)", "7"),
    ("Slaad Verde", 277, "127 (15d10 + 45)", "8"),
    ("Slaad Grigio", 277, "127 (17d8 + 51)", "9"),
    ("Slaad della Morte", 278, "170 (20d8 + 80)", "10"),
    ("Spaventapasseri", 279, "36 (8d8)", "1"),
    ("Spettro", 280, "22 (5d8)", "1"),
])
def test_original_statblocks(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_lore_pages_are_not_extra_monsters():
    assert len(mm.MONSTERS) == 9
    assert all(d["page"] not in (274, 275) for d in mm.MONSTERS.values())
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 9
    with pytest.raises(ValueError, match="not_an_original_statblock"):
        mm.audit("Slaad", catalog())


def test_separate_slaad_variants_and_sphinx():
    assert len([n for n in mm.MONSTERS if n.startswith("Slaad")]) == 6
    r = mm.audit("Ginosfinge", catalog())
    assert len(r["attributes"]["azioni_leggendarie_nomi_da_completare"]) == 3


def test_wrong_source_collision_mutation_and_copy():
    c = catalog()
    c["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Spettro", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Spettro", catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Spettro", catalog(), same_named_monster=True)
    previous = deepcopy(mm.MONSTERS["Slaad Blu"])
    try:
        mm.MONSTERS["Slaad Blu"]["hp"] = "124 (13d10 + 52)"
        with pytest.raises(ValueError, match="source_fields_changed"):
            mm.audit("Slaad Blu", catalog())
    finally:
        mm.MONSTERS["Slaad Blu"] = previous
    x = mm.audit("Slaad della Morte", catalog())
    x["attributes"]["caratteristiche"]["cos"] = "99"
    assert mm.audit("Slaad della Morte", catalog())["attributes"]["caratteristiche"]["cos"] == "19"
