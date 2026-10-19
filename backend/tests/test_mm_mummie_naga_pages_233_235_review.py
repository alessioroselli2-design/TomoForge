"""Original Italian MM pp233–235: signed source and fail-closed gates."""
from copy import deepcopy
import pytest
from services import mm_mummie_naga_pages_233_235_review as mm


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
    ("Signore delle Mummie", 233, "97 (13d8 + 39)", "15"),
    ("Naga d'Ossa", 234, "58 (9d10 + 9)", "4"),
    ("Naga Spirituale", 235, "75 (10d10 + 20)", "8"),
    ("Naga Guardiana", 235, "127 (15d10 + 45)", "10"),
])
def test_source_signed_statblocks(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_naga_are_two_independent_blocks_same_page():
    assert len(mm.MONSTERS) == 4
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 4
    assert mm.audit("Naga Spirituale", catalog())["physical_page"] == 235
    assert mm.audit("Naga Guardiana", catalog())["physical_page"] == 235
    with pytest.raises(ValueError, match="not_an_original_statblock"):
        mm.audit("Naga", catalog())


def test_legendary_actions_preserved():
    r = mm.audit("Signore delle Mummie", catalog())
    assert "Turbine di Sabbia" in r["attributes"]["azioni_leggendarie_nomi_da_completare"]


def test_source_mismatch_collision_and_mutation_fail_closed():
    c = catalog()
    c["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Naga d'Ossa", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Naga Guardiana", catalog(), same_named_monster=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Naga Guardiana", catalog(), existing_id=True)
    saved = deepcopy(mm.MONSTERS["Naga Spirituale"])
    try:
        mm.MONSTERS["Naga Spirituale"]["hp"] = "80 (10d10 + 20)"
        with pytest.raises(ValueError, match="source_fields_changed"):
            mm.audit("Naga Spirituale", catalog())
    finally:
        mm.MONSTERS["Naga Spirituale"] = saved


def test_defensive_copy():
    o = mm.audit("Signore delle Mummie", catalog())
    o["attributes"]["caratteristiche"]["for"] = "99"
    assert mm.audit("Signore delle Mummie", catalog())["attributes"]["caratteristiche"]["for"] == "18"
