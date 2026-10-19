"""Source and negative regressions for MM pp219-224."""
from copy import deepcopy
import pytest
from services import mm_merrow_miconidi_mimic_pages_219_224_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID, "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256, "physical_pages": mm.PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }


@pytest.mark.parametrize("name,page,hp,gs", [
    ("Merrow", 219, "45 (6d10 + 12)", "2"),
    ("Mezzodrago Rosso Veterano", 220, "65 (10d8 + 20)", "5"),
    ("Miconide Germoglio", 221, "7 (2d6)", "0"),
    ("Quaggoth Servitore delle Spore", 221, "45 (6d8 + 18)", "1"),
    ("Miconide Adulto", 223, "22 (4d8 + 4)", "1/2"),
    ("Miconide Sovrano", 223, "60 (8d10 + 16)", "2"),
    ("Mimic", 224, "58 (9d8 + 18)", "2"),
])
def test_source_statblocks(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_two_statblocks_same_page_and_no_art_page_222():
    assert len(mm.MONSTERS) == 7
    assert 222 not in [mm.audit(n, catalog())["physical_page"] for n in mm.MONSTERS]
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 7
    with pytest.raises(ValueError, match="not_a_source_statblock"):
        mm.audit("Miconidi", catalog())


def test_wrong_authority_collision_mutation():
    c = catalog()
    c["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Miconide Adulto", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Miconide Adulto", catalog(), same_named_monster=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Mimic", catalog(), existing_id=True)
    original = deepcopy(mm.MONSTERS["Mimic"])
    try:
        mm.MONSTERS["Mimic"]["gs"] = "22"
        with pytest.raises(ValueError, match="original_source_fields_changed"):
            mm.audit("Mimic", catalog())
    finally:
        mm.MONSTERS["Mimic"] = original
