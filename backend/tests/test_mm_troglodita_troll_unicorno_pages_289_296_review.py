"""Original-vision core statblock checks and negative controls on pp289-296."""
from copy import deepcopy
import pytest
from services import mm_troglodita_troll_unicorno_pages_289_296_review as mm


def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }


@pytest.mark.parametrize("name,page,hp,gs", [
    ("Troglodita", 289, "13 (2d8 + 4)", "1/4"),
    ("Troll", 290, "84 (8d10 + 40)", "5"),
    ("Uccello Stigeo", 291, "2 (1d4)", "1/8"),
    ("Umber Hulk", 292, "93 (11d10 + 33)", "5"),
    ("Unicorno", 294, "67 (9d10 + 18)", "5"),
])
def test_statblock_individual_from_scan(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert r["writes"]==0


def test_exactly_five_boxes_and_no_vampire_lore_false_statblock():
    assert len(mm.MONSTERS)==5
    assert len({mm.audit(n,catalog())["id"] for n in mm.MONSTERS})==5
    assert {r["page"] for r in mm.MONSTERS.values()}.isdisjoint({293,295,296})
    with pytest.raises(ValueError,match="not_an_original_statblock"):
        mm.audit("La Tana di un Vampiro",catalog())


def test_unicorn_legendaries_and_wrong_source():
    assert len(mm.audit("Unicorno",catalog())["attributes"]["azioni_leggendarie_nomi_da_completare"])==3
    c=catalog()
    c["physical_sha256"]="wrong"
    with pytest.raises(ValueError,match="original_source_mismatch"):
        mm.audit("Unicorno",c)


def test_collision_mutation_and_copy():
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit("Troll",catalog(),same_named_monster=True)
    old=deepcopy(mm.MONSTERS["Troglodita"])
    try:
        mm.MONSTERS["Troglodita"]["ac"]="15"
        with pytest.raises(ValueError,match="source_fields_changed"):
            mm.audit("Troglodita",catalog())
    finally:
        mm.MONSTERS["Troglodita"]=old
    attrs=mm.audit("Unicorno",catalog())["attributes"]
    attrs["caratteristiche"]["car"]="99"
    assert mm.audit("Unicorno",catalog())["attributes"]["caratteristiche"]["car"]=="16"
