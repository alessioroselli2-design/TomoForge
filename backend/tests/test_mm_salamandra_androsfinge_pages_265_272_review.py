"""MM p265–272: seven statblocks and cross-source skeleton dedup."""
from copy import deepcopy
import pytest
from services import mm_salamandra_androsfinge_pages_265_272_review as mm


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
    ("Salamandra", 265, "90 (12d10 + 24)", "5"),
    ("Satiro", 266, "31 (7d8)", "1/2"),
    ("Scheletro Minotauro", 268, "67 (9d10 + 18)", "2"),
    ("Scheletro Cavallo da Guerra", 268, "22 (3d10 + 6)", "1/2"),
    ("Sciacallo Mannaro", 269, "18 (4d8)", "1/2"),
    ("Segugio Infernale", 270, "45 (7d8 + 14)", "3"),
    ("Androsfinge", 272, "199 (19d10 + 95)", "17"),
])
def test_source_core(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_skeleton_cross_source_no_duplicate():
    assert len(mm.MONSTERS) == 7
    assert mm.CROSS_SOURCE_OVERLAP["name"] == "Scheletro"
    assert mm.CROSS_SOURCE_OVERLAP["physical_page"] == 267
    assert mm.CROSS_SOURCE_OVERLAP["resolution"] == "reuse_record_no_duplicate"
    assert mm.CROSS_SOURCE_OVERLAP["full_statblock_confirmed"] is False
    with pytest.raises(ValueError, match="cross_source_existing_skeleton"):
        mm.audit("Scheletro", catalog())
    assert 271 not in {x["page"] for x in mm.MONSTERS.values()}
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 7


def test_source_mutation_and_collision_guards():
    bad = catalog()
    bad["physical_sha256"] = "different"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Satiro", bad)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Satiro", catalog(), same_named_monster=True)
    saved = deepcopy(mm.MONSTERS["Androsfinge"])
    try:
        mm.MONSTERS["Androsfinge"]["hp"] = "200 (19d10 + 95)"
        with pytest.raises(ValueError, match="original_source_fields_changed"):
            mm.audit("Androsfinge", catalog())
    finally:
        mm.MONSTERS["Androsfinge"] = saved


def test_legendary_and_copy_isolation():
    a = mm.audit("Androsfinge", catalog())
    assert a["attributes"]["azioni_leggendarie_nomi_da_completare"]
    a["attributes"]["caratteristiche"]["for"] = "99"
    assert mm.audit("Androsfinge", catalog())["attributes"]["caratteristiche"]["for"] == "22"
