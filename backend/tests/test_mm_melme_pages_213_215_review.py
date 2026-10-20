"""Fail-closed original-source audit of four oozes on pp213-215."""
from copy import deepcopy
import pytest
from services import mm_melme_pages_213_215_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID, "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256, "physical_pages": mm.PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }


@pytest.mark.parametrize("name,page,hp,gs", [
    ("Ameba Paglierina", 213, "45 (6d10 + 12)", "2"),
    ("Cubo Gelatinoso", 214, "84 (8d10 + 40)", "2"),
    ("Melma Grigia", 215, "22 (3d8 + 9)", "1/2"),
    ("Protoplasma Nero", 215, "85 (10d10 + 30)", "4"),
])
def test_independent_source_statblocks(name, page, hp, gs):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == gs
    assert result["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert result["writes"] == 0


def test_page_212_lore_not_invented_and_two_independent_p215():
    assert len(mm.MONSTERS) == 4
    assert 212 not in {mm.audit(n, catalog())["physical_page"] for n in mm.MONSTERS}
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 4
    with pytest.raises(ValueError, match="not_a_source_statblock"):
        mm.audit("Melma", catalog())


def test_authority_collision_mutation_fail_closed():
    c = catalog()
    c["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Cubo Gelatinoso", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Cubo Gelatinoso", catalog(), same_named_monster=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Cubo Gelatinoso", catalog(), existing_id=True)
    before = deepcopy(mm.MONSTERS["Protoplasma Nero"])
    try:
        mm.MONSTERS["Protoplasma Nero"]["hp"] = "84 (10d10 + 30)"
        with pytest.raises(ValueError, match="original_source_fields_changed"):
            mm.audit("Protoplasma Nero", catalog())
    finally:
        mm.MONSTERS["Protoplasma Nero"] = before


def test_defensive_copy():
    a = mm.audit("Ameba Paglierina", catalog())
    a["attributes"]["tratti_nomi_da_completare"].append("Inventato")
    b = mm.audit("Ameba Paglierina", catalog())
    assert "Inventato" not in b["attributes"]["tratti_nomi_da_completare"]
