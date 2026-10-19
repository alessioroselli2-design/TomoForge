"""Source and no-duplicate gates for MM pp265-272."""
from copy import deepcopy
import pytest
from services import mm_salamandra_satiro_scheletri_sfinge_pages_265_272_review as mm


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
def test_seven_source_statblocks(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_overlap_scheletro_and_lore_sphinx():
    assert len(mm.MONSTERS) == 7
    assert mm.CROSS_SOURCE_OVERLAP["name"] == "Scheletro"
    assert mm.CROSS_SOURCE_OVERLAP["page"] == 267
    assert mm.CROSS_SOURCE_OVERLAP["not_confirmed_full_fields"] is True
    assert 271 not in [r["page"] for r in mm.MONSTERS.values()]
    with pytest.raises(ValueError, match="already_verified_cross_source"):
        mm.audit("Scheletro", catalog())
    with pytest.raises(ValueError, match="not_an_original_statblock"):
        mm.audit("Sfinge", catalog())


def test_multiple_skeletons_are_separate_unique_boxes():
    assert mm.audit("Scheletro Minotauro", catalog())["physical_page"] == 268
    assert mm.audit("Scheletro Cavallo da Guerra", catalog())["physical_page"] == 268
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 7


def test_legendary_sphinx_names_and_fail_closed():
    a = mm.audit("Androsfinge", catalog())["attributes"]
    assert len(a["azioni_leggendarie_nomi_da_completare"]) == 3
    c = catalog()
    c["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Androsfinge", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Androsfinge", catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Androsfinge", catalog(), same_named_monster=True)


def test_fingerprint_and_defensive_copy():
    backup = deepcopy(mm.MONSTERS["Satiro"])
    try:
        mm.MONSTERS["Satiro"]["hp"] = "32 (7d8)"
        with pytest.raises(ValueError, match="source_fields_changed"):
            mm.audit("Satiro", catalog())
    finally:
        mm.MONSTERS["Satiro"] = backup
    x = mm.audit("Salamandra", catalog())
    x["attributes"]["caratteristiche"]["for"] = "99"
    assert mm.audit("Salamandra", catalog())["attributes"]["caratteristiche"]["for"] == "18"
