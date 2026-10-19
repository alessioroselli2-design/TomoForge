"""Fail-closed original visual-source checks p325–332 and PHB overlaps."""
from copy import deepcopy
import pytest
from services import mm_appendix_a_beasts_pages_325_332_review as mm

def catalog():
    return {"logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
      "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
      "source_status":"active","source_role":"authority",
      "authority_class":"licensed_translation","text_mode":"vision_required"}

@pytest.mark.parametrize("name,page,hp,gs",[
    ("Gorilla",325,"19 (3d8 + 6)","1/2"),
    ("Gorilla Gigante",325,"157 (15d12 + 60)","7"),
    ("Granchio",325,"2 (1d4)","0"),
    ("Granchio Gigante",325,"13 (3d8)","1/8"),
    ("Gufo Gigante",326,"19 (3d10 + 3)","1/4"),
    ("Iena",326,"5 (1d8 + 1)","0"),
    ("Iena Gigante",326,"45 (6d10 + 12)","1"),
    ("Lucertola",327,"2 (1d4)","0"),
    ("Lucertola Gigante",327,"19 (3d10 + 3)","1/4"),
    ("Lupo Invernale",328,"75 (10d10 + 20)","3"),
    ("Mammut",328,"126 (11d12 + 55)","6"),
    ("Millepiedi Gigante",329,"4 (1d6 + 1)","1/4"),
    ("Orca Assassina",329,"90 (12d12 + 12)","3"),
    ("Orso Polare",330,"42 (5d10 + 15)","2"),
    ("Piovra",330,"3 (1d6)","0"),
    ("Piovra Gigante",331,"52 (8d10 + 8)","1"),
    ("Pipistrello Gigante",331,"22 (4d10)","1/4"),
    ("Pony",331,"11 (2d8 + 2)","1/8"),
    ("Quipper",332,"1 (1d4 - 1)","0"),
    ("Ragno",332,"1 (1d4 - 1)","0"),
])
def test_statblocks(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert r["writes"]==0

def test_exact_count_and_gorilla_gufo_source():
    assert len(mm.MONSTERS)==20 and len(mm.PHB_OVERLAPS)==11
    assert mm.audit("Gorilla Gigante",catalog())["physical_page"]==325
    assert mm.audit("Gufo Gigante",catalog())["physical_page"]==326
    assert len({mm.audit(n,catalog())["id"] for n in mm.MONSTERS})==20
    for name in mm.PHB_OVERLAPS:
        with pytest.raises(ValueError,match="existing_phb_monster_needs_full_comparison"):
            mm.audit(name,catalog())

def test_source_collision_mutation_defensive_copy():
    c=catalog();c["physical_sha256"]="other"
    with pytest.raises(ValueError,match="original_source_mismatch"):
        mm.audit("Gorilla Gigante",c)
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit("Ragno",catalog(),same_named_monster=True)
    old=deepcopy(mm.MONSTERS["Mammut"])
    try:
        mm.MONSTERS["Mammut"]["hp"]="127 (11d12 + 55)"
        with pytest.raises(ValueError,match="source_fields_changed"):
            mm.audit("Mammut",catalog())
    finally:
        mm.MONSTERS["Mammut"]=old
    r=mm.audit("Gorilla",catalog())
    r["attributes"]["caratteristiche"]["for"]="0"
    assert mm.audit("Gorilla",catalog())["attributes"]["caratteristiche"]["for"]=="16"


def test_exhaustive_cross_manual_collision_protection():
    assert mm.PHB_OVERLAPS == frozenset({
        "Gufo", "Leone", "Lupo", "Lupo Feroce", "Mastino", "Mulo",
        "Orso Bruno", "Orso Nero", "Pantera", "Pipistrello", "Ragno Gigante",
    })
    assert set(mm.MONSTERS).isdisjoint(mm.PHB_OVERLAPS)
    assert len([x for x in mm.MONSTERS.values() if x["page"] == 325]) == 4
    assert len([x for x in mm.MONSTERS.values() if x["page"] == 326]) == 3
    for n in mm.PHB_OVERLAPS:
        with pytest.raises(ValueError, match="existing_phb_monster_needs_full_comparison"):
            mm.audit(n, catalog())
