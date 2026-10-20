"""Direct visual-source p226–232 statblock and negative-gate tests."""
from copy import deepcopy

import pytest

from services import mm_mindflayer_modron_mummia_pages_226_232_review as mm


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
    ("Mind Flayer", 226, "71 (13d8 + 13)", "7"),
    ("Minotauro", 227, "76 (9d10 + 27)", "3"),
    ("Monodrone", 228, "5 (1d8 + 1)", "1/8"),
    ("Duodrone", 229, "11 (2d8 + 2)", "1/4"),
    ("Tridrone", 229, "16 (3d8 + 3)", "1/2"),
    ("Quadrone", 230, "22 (4d8 + 4)", "1"),
    ("Pentadrone", 230, "32 (5d10 + 5)", "2"),
    ("Mummia", 232, "58 (9d8 + 18)", "3"),
])
def test_original_independent_statblocks(name, page, hp, gs):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == gs
    assert result["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert result["writes"] == 0


def test_no_false_statblocks_from_lore_and_variants():
    assert len(mm.MONSTERS) == 8
    assert {mm.audit(n, catalog())["physical_page"] for n in mm.MONSTERS} == {
        226, 227, 228, 229, 230, 232,
    }
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 8
    for fake in ("Modron", "Mind Flayer Arcanista", "Modron Fuori Controllo"):
        with pytest.raises(ValueError, match="not_a_source_statblock"):
            mm.audit(fake, catalog())
    assert "GS 8" in mm.audit("Mind Flayer", catalog())["attributes"]["varianti_nomi_da_completare"][0]


def test_source_and_collision_fail_closed():
    bad = catalog()
    bad["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Mummia", bad)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Mummia", catalog(), same_named_monster=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Mummia", catalog(), existing_id=True)


def test_mutation_detection_and_defensive_copy():
    original = deepcopy(mm.MONSTERS["Quadrone"])
    try:
        mm.MONSTERS["Quadrone"]["hp"] = "22 (5d8 + 4)"
        with pytest.raises(ValueError, match="original_source_fields_changed"):
            mm.audit("Quadrone", catalog())
    finally:
        mm.MONSTERS["Quadrone"] = original
    a = mm.audit("Mummia", catalog())
    a["attributes"]["caratteristiche"]["cos"] = "999"
    assert mm.audit("Mummia", catalog())["attributes"]["caratteristiche"]["cos"] == "15"
