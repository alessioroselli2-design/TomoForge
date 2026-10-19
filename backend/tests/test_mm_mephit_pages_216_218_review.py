"""Source proof and negative controls for Italian MM six mephits pp216-218."""
from copy import deepcopy
import pytest
from services import mm_mephit_pages_216_218_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID, "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256, "physical_pages": mm.PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }


@pytest.mark.parametrize("name,page,hp,gs", [
    ("Mephit del Fango", 216, "27 (6d6 + 6)", "1/4"),
    ("Mephit del Fumo", 216, "22 (5d6 + 5)", "1/4"),
    ("Mephit del Ghiaccio", 217, "21 (6d6)", "1/2"),
    ("Mephit del Magma", 217, "22 (5d6 + 5)", "1/2"),
    ("Mephit del Vapore", 218, "21 (6d6)", "1/4"),
    ("Mephit della Polvere", 218, "17 (5d6)", "1/2"),
])
def test_six_distinct_statblocks(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_generic_heading_not_a_seventh_creature():
    assert len(mm.MONSTERS) == 6
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 6
    with pytest.raises(ValueError, match="not_a_source_statblock"):
        mm.audit("Mephit", catalog())


def test_authority_and_collision_guards():
    c = catalog()
    c["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Mephit del Fumo", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Mephit del Fumo", catalog(), same_named_monster=True)
    original = deepcopy(mm.MONSTERS["Mephit del Magma"])
    try:
        mm.MONSTERS["Mephit del Magma"]["ac"] = "19"
        with pytest.raises(ValueError, match="original_source_fields_changed"):
            mm.audit("Mephit del Magma", catalog())
    finally:
        mm.MONSTERS["Mephit del Magma"] = original


def test_copy_protection():
    r = mm.audit("Mephit del Fango", catalog())
    r["attributes"]["azioni_nomi_da_completare"].clear()
    assert mm.audit("Mephit del Fango", catalog())["attributes"]["azioni_nomi_da_completare"]
