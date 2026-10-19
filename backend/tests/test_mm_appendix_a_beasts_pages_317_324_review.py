"""MM Appendix A p317–324 guarded core source tests."""
from copy import deepcopy
import pytest
from services import mm_appendix_a_beasts_pages_317_324_review as mm

def catalog():
    return {"logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required"}

@pytest.mark.parametrize("name,page,hp,gs",[
    ("Albero Risvegliato", 317, "59 (7d12 + 14)", "2"),
    ("Alce", 317, "13 (2d10 + 2)", "1/4"),
    ("Alce Gigante", 317, "42 (5d12 + 10)", "2"),
    ("Aquila", 317, "3 (1d6)", "0"),
    ("Avvoltoio", 318, "5 (1d8 + 1)", "0"),
    ("Avvoltoio Gigante", 318, "22 (3d10 + 6)", "1"),
    ("Babbuino", 318, "3 (1d6)", "0"),
    ("Beccoaguzzo", 319, "19 (3d10 + 3)", "1/4"),
    ("Cammello", 319, "15 (2d10 + 4)", "1/8"),
    ("Cane della Morte", 319, "39 (6d8 + 12)", "1"),
    ("Cane Intermittente", 320, "22 (4d8 + 4)", "1/4"),
    ("Capra", 320, "4 (1d8)", "0"),
    ("Capra Gigante", 320, "19 (3d10 + 3)", "1/2"),
    ("Cavallo da Tiro", 321, "19 (3d10 + 3)", "1/4"),
    ("Cavalluccio Marino", 321, "1 (1d4 - 1)", "0"),
    ("Cavalluccio Marino Gigante", 321, "16 (3d10)", "1/2"),
    ("Cespuglio Risvegliato", 322, "10 (3d6)", "0"),
    ("Cinghiale Gigante", 322, "42 (5d10 + 15)", "2"),
    ("Coccodrillo Gigante", 323, "85 (9d12 + 27)", "5"),
    ("Daino", 323, "4 (1d8)", "0"),
    ("Elefante", 323, "76 (8d12 + 24)", "4"),
    ("Faina", 324, "1 (1d4 - 1)", "0"),
    ("Faina Gigante", 324, "9 (2d8)", "1/8"),
    ("Falco di Sangue", 324, "7 (2d6)", "1/8"),
])
def test_exact_original_statblocks(name,page,hp,gs):
    x=mm.audit(name,catalog())
    assert x["physical_page"]==page
    assert x["attributes"]["punti_ferita"]==hp
    assert x["attributes"]["grado_sfida"]==gs
    assert x["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert x["writes"]==0

def test_census_and_cross_source_guard():
    assert len(mm.MONSTERS)==24
    assert len(mm.EXISTING_CROSS_SOURCE_NAMES)==8
    assert "Alce Gigante" in mm.MONSTERS and mm.MONSTERS["Alce Gigante"]["page"]==317
    assert "Aquila" in mm.MONSTERS and mm.MONSTERS["Aquila"]["page"]==317
    assert sum(v["page"]==317 for v in mm.MONSTERS.values())==4
    assert sum(v["page"]==318 for v in mm.MONSTERS.values())==3
    assert len({mm.audit(n,catalog())["id"] for n in mm.MONSTERS})==24
    for name in mm.EXISTING_CROSS_SOURCE_NAMES:
        with pytest.raises(ValueError,match="existing_phb_monster_requires_full_comparison"):
            mm.audit(name,catalog())

def test_fail_closed_source_collision_mutation():
    c=catalog();c["physical_sha256"]="wrong"
    with pytest.raises(ValueError,match="original_source_mismatch"):
        mm.audit("Alce",c)
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit("Alce",catalog(),same_named_monster=True)
    old=deepcopy(mm.MONSTERS["Elefante"])
    try:
        mm.MONSTERS["Elefante"]["gs"]="99"
        with pytest.raises(ValueError,match="source_fields_changed"):
            mm.audit("Elefante",catalog())
    finally:
        mm.MONSTERS["Elefante"]=old

def test_defensive_copy():
    x=mm.audit("Cane Intermittente",catalog())
    x["attributes"]["caratteristiche"]["for"]="0"
    assert mm.audit("Cane Intermittente",catalog())["attributes"]["caratteristiche"]["for"]=="12"
