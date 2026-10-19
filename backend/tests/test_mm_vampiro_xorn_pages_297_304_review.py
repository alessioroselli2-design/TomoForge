"""Source identity, math and collision regressions on MM pp297–304."""
from copy import deepcopy
import pytest
from services import mm_vampiro_xorn_pages_297_304_review as mm


def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }


@pytest.mark.parametrize("name,page,hp,gs", [
    ("Vampiro", 297, "144 (17d8 + 68)", "13"),
    ("Progenie Vampirica", 298, "82 (11d8 + 33)", "5"),
    ("Verme Purpureo", 299, "247 (15d20 + 90)", "15"),
    ("Vermeiena", 300, "51 (6d10 + 18)", "2"),
    ("Viverna", 301, "110 (13d10 + 39)", "6"),
    ("Wight", 302, "45 (6d8 + 18)", "3"),
    ("Wraith", 303, "67 (9d8 + 27)", "5"),
    ("Xorn", 304, "73 (7d8 + 42)", "5"),
])
def test_statblocks(name,page,hp,gs):
    item=mm.audit(name,catalog())
    assert item["physical_page"]==page
    assert item["attributes"]["punti_ferita"]==hp
    assert item["attributes"]["grado_sfida"]==gs
    assert item["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert item["writes"]==0


def test_one_box_per_page_no_false_vampire_duplicates():
    assert len(mm.MONSTERS)==8
    assert len({mm.audit(n,catalog())["id"] for n in mm.MONSTERS})==8
    assert "GS 15" in mm.audit("Vampiro",catalog())["attributes"]["varianti_nomi_da_completare"][0]
    with pytest.raises(ValueError,match="not_a_source_statblock"):
        mm.audit("Vampiro Incantatore",catalog())


def test_fail_closed_source_and_collision():
    c=catalog()
    c["physical_sha256"]="wrong"
    with pytest.raises(ValueError,match="original_source_mismatch"):
        mm.audit("Wraith",c)
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit("Wraith",catalog(),same_named_monster=True)


def test_mutated_fields_and_defensive_copy():
    old=deepcopy(mm.MONSTERS["Xorn"])
    try:
        mm.MONSTERS["Xorn"]["hp"]="73 (7d8 + 41)"
        with pytest.raises(ValueError,match="source_fields_changed"):
            mm.audit("Xorn",catalog())
    finally:
        mm.MONSTERS["Xorn"]=old
    item=mm.audit("Verme Purpureo",catalog())
    item["attributes"]["caratteristiche"]["for"]="0"
    assert mm.audit("Verme Purpureo",catalog())["attributes"]["caratteristiche"]["for"]=="28"
