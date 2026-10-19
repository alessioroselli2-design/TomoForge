"""Fail-closed source audit pp236-240: named boxes, HP and mutation regression."""
from copy import deepcopy
import pytest
from services import mm_nothic_oggetti_ogre_pages_236_240_review as mm


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
    ("Nothic", 236, "45 (6d8 + 18)", "2"),
    ("Armatura Animata", 237, "33 (6d8 + 6)", "1"),
    ("Spada Volante", 238, "17 (5d6)", "1/4"),
    ("Tappeto Soffocante", 238, "33 (6d10)", "2"),
    ("Ogre", 239, "59 (7d10 + 21)", "2"),
    ("Mezzogre", 240, "30 (4d10 + 8)", "1"),
])
def test_source_fields(name, page, hp, gs):
    v = mm.audit(name, catalog())
    assert v["physical_page"] == page
    assert v["attributes"]["punti_ferita"] == hp
    assert v["attributes"]["grado_sfida"] == gs
    assert v["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert v["writes"] == 0


def test_six_distinct_p236_240():
    assert len(mm.MONSTERS) == 6
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 6
    assert mm.audit("Spada Volante", catalog())["physical_page"] == 238
    assert mm.audit("Tappeto Soffocante", catalog())["physical_page"] == 238
    with pytest.raises(ValueError, match="not_an_original_statblock"):
        mm.audit("Oggetto Animato", catalog())


def test_negative_guards():
    c = catalog()
    c["physical_sha256"] = "other"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Nothic", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Nothic", catalog(), same_named_monster=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Ogre", catalog(), existing_id=True)
    backup = deepcopy(mm.MONSTERS["Ogre"])
    try:
        mm.MONSTERS["Ogre"]["gs"] = "9"
        with pytest.raises(ValueError, match="source_fields_changed"):
            mm.audit("Ogre", catalog())
    finally:
        mm.MONSTERS["Ogre"] = backup


def test_defensive_copy():
    v = mm.audit("Tappeto Soffocante", catalog())
    v["attributes"]["caratteristiche"]["for"] = "100"
    assert mm.audit("Tappeto Soffocante", catalog())["attributes"]["caratteristiche"]["for"] == "17"
