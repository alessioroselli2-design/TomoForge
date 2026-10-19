"""Original MM pp241–248: eight independently boxed statblocks and negative checks."""
from copy import deepcopy
import pytest
from services import mm_ombra_orchi_orrore_pages_241_248_review as mm


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
    ("Ombra", 241, "16 (3d8 + 3)", "1/2"),
    ("Omuncolo", 242, "5 (2d4)", "0"),
    ("Oni", 243, "110 (13d10 + 39)", "7"),
    ("Orco", 246, "15 (2d8 + 6)", "1/2"),
    ("Orco Capotribù Guerriero", 246, "93 (11d8 + 44)", "4"),
    ("Orco Occhio di Gruumsh", 247, "45 (6d8 + 18)", "2"),
    ("Orog", 247, "42 (5d8 + 20)", "2"),
    ("Orrore Corazzato", 248, "60 (8d8 + 24)", "4"),
])
def test_source_statistics(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_orc_statblock_count_and_no_lore_imposter():
    assert len(mm.MONSTERS) == 8
    assert 244 not in [v["page"] for v in mm.MONSTERS.values()]
    assert 245 not in [v["page"] for v in mm.MONSTERS.values()]
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 8
    with pytest.raises(ValueError, match="not_an_original_statblock"):
        mm.audit("Orco Occhio", catalog())


def test_source_identity_and_collision_fail_closed():
    c = catalog()
    c["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Orog", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Orog", catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Orog", catalog(), same_named_monster=True)
    saved = deepcopy(mm.MONSTERS["Orrore Corazzato"])
    try:
        mm.MONSTERS["Orrore Corazzato"]["hp"] = "60 (8d8 + 23)"
        with pytest.raises(ValueError, match="source_fields_changed"):
            mm.audit("Orrore Corazzato", catalog())
    finally:
        mm.MONSTERS["Orrore Corazzato"] = saved


def test_copy_isolation():
    x = mm.audit("Ombra", catalog())
    x["attributes"]["caratteristiche"]["for"] = "99"
    assert mm.audit("Ombra", catalog())["attributes"]["caratteristiche"]["for"] == "6"
