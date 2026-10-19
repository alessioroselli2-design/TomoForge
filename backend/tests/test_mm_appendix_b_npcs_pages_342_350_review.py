"""Source-backed Appendix B core checks; NPC != PC, no duplicate writes."""
from copy import deepcopy
import pytest
from services import mm_appendix_b_npcs_pages_342_350_review as mm

def catalog():
    return {"logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
      "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
      "source_status":"active","source_role":"authority",
      "authority_class":"licensed_translation","text_mode":"vision_required"}

@pytest.mark.parametrize("name,page,hp,gs",[
  ("Accolito",342,"9 (2d8)","1/4"),
  ("Arcimago",342,"99 (18d8 + 18)","12"),
  ("Assassino",343,"78 (12d8 + 24)","8"),
  ("Bandito",343,"11 (2d8 + 2)","1/8"),
  ("Berserker",344,"67 (9d8 + 27)","2"),
  ("Capo dei Banditi",344,"65 (10d8 + 20)","2"),
  ("Cavaliere",344,"52 (8d8 + 16)","3"),
  ("Combattente Tribale",345,"11 (2d8 + 2)","1/8"),
  ("Cultista",345,"9 (2d8)","1/8"),
  ("Cultista Fanatico",346,"33 (6d8 + 6)","2"),
  ("Druido",346,"27 (5d8 + 5)","2"),
  ("Esploratore",347,"16 (3d8 + 3)","1/2"),
  ("Gladiatore",347,"112 (15d8 + 45)","5"),
  ("Guardia",348,"11 (2d8 + 2)","1/8"),
  ("Mago",348,"40 (9d8)","6"),
  ("Malvivente",348,"32 (5d8 + 10)","1/2"),
  ("Nobile",349,"9 (2d8)","1/8"),
  ("Popolano",349,"4 (1d8)","0"),
  ("Sacerdote",350,"27 (5d8 + 5)","2"),
  ("Spia",350,"27 (6d8)","1"),
  ("Veterano",350,"58 (9d8 + 18)","3"),
])
def test_each_npc_source_stats(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert r["writes"]==0

def test_complete_appendix_b_npc_inventory_and_source_speed():
    assert len(mm.MONSTERS)==21
    assert {n for n,v in mm.MONSTERS.items() if v["page"]==350}=={"Sacerdote","Spia","Veterano"}
    assert mm.audit("Sacerdote",catalog())["attributes"]["velocita"]=="7,5 m"
    assert len({mm.audit(n,catalog())["id"] for n in mm.MONSTERS})==21
    with pytest.raises(ValueError,match="not_a_source_npc_statblock"):
        mm.audit("Famiglio",catalog())

def test_fail_closed_authority_and_collision():
    c=catalog();c["physical_sha256"]="invalid"
    with pytest.raises(ValueError,match="original_source_mismatch"):
        mm.audit("Arcimago",c)
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit("Arcimago",catalog(),same_named_monster=True)

def test_mutation_and_defensive_copy():
    old=deepcopy(mm.MONSTERS["Accolito"])
    try:
        mm.MONSTERS["Accolito"]["hp"]="9 (2d8 + 1)"
        with pytest.raises(ValueError,match="source_fields_modified"):
            mm.audit("Accolito",catalog())
    finally:
        mm.MONSTERS["Accolito"]=old
    v=mm.audit("Veterano",catalog())
    v["attributes"]["caratteristiche"]["for"]="0"
    assert mm.audit("Veterano",catalog())["attributes"]["caratteristiche"]["for"]=="16"
