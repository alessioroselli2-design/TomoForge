"""Original-source statblock checks p333–341, six PHB overlaps and variants."""
from copy import deepcopy
import pytest
from services import mm_appendix_a_sciami_pages_333_341_review as mm

def catalog():
    return {"logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
      "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
      "source_status":"active","source_role":"authority",
      "authority_class":"licensed_translation","text_mode":"vision_required"}

@pytest.mark.parametrize("name,page,hp,gs",[
    ("Ragno Lupo Gigante",333,"11 (2d8 + 2)","1/4"),
    ("Ragno-Fase",333,"32 (5d10 + 5)","3"),
    ("Rana Gigante",334,"18 (4d8)","1/4"),
    ("Rinoceronte",334,"45 (6d10 + 12)","2"),
    ("Rospo Gigante",334,"39 (6d10 + 6)","1"),
    ("Scarabeo di Fuoco Gigante",335,"4 (1d6 + 1)","0"),
    ("Sciacallo",335,"3 (1d6)","0"),
    ("Sciame di Corvi",335,"24 (7d8 - 7)","1/4"),
    ("Sciame di Insetti",335,"22 (5d8)","1/2"),
    ("Sciame di Pipistrelli",336,"22 (5d8)","1/4"),
    ("Sciame di Quipper",336,"28 (8d8 - 8)","1"),
    ("Sciame di Serpenti Velenosi",336,"36 (8d8)","2"),
    ("Sciame di Topi",337,"24 (7d8 - 7)","1/4"),
    ("Scorpione",337,"1 (1d4 - 1)","0"),
    ("Scorpione Gigante",337,"52 (7d10 + 14)","3"),
    ("Serpente Stritolatore Gigante",338,"60 (8d12 + 8)","2"),
    ("Serpente Velenoso Gigante",338,"11 (2d8 + 2)","1/4"),
    ("Serpente Volante",338,"5 (2d4)","1/8"),
    ("Squalo Cacciatore",338,"45 (6d10 + 12)","2"),
    ("Squalo Gigante",339,"126 (11d12 + 55)","5"),
    ("Tasso",339,"3 (1d4 + 1)","0"),
    ("Tasso Gigante",339,"13 (2d8 + 4)","1/4"),
    ("Tigre dai Denti a Sciabola",340,"52 (7d10 + 14)","2"),
    ("Topo Gigante",340,"7 (2d6)","1/8"),
    ("Vespa Gigante",341,"13 (3d8)","1/2"),
    ("Worg",341,"26 (4d10 + 4)","1/2"),
])
def test_exact_original_stats(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert r["writes"]==0

def test_no_false_subtype_monster_and_phb_duplicates():
    assert len(mm.MONSTERS)==26 and len(mm.PHB_OVERLAPS)==6
    assert len({mm.audit(n,catalog())["id"] for n in mm.MONSTERS})==26
    for n in mm.PHB_OVERLAPS:
        with pytest.raises(ValueError,match="existing_phb_monster_requires_full_comparison"):
            mm.audit(n,catalog())
    for n in ("Topo Gigante Contagioso","Sciame di Ragni"):
        with pytest.raises(ValueError,match="not_a_source_statblock"):
            mm.audit(n,catalog())

def test_source_collision_and_tamper_fail_closed():
    c=catalog();c["physical_sha256"]="invalid"
    with pytest.raises(ValueError,match="original_source_mismatch"):
        mm.audit("Worg",c)
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit("Worg",catalog(),same_named_monster=True)
    prev=deepcopy(mm.MONSTERS["Scorpione Gigante"])
    try:
        mm.MONSTERS["Scorpione Gigante"]["hp"]="55 (7d10 + 14)"
        with pytest.raises(ValueError,match="original_source_fields_changed"):
            mm.audit("Scorpione Gigante",catalog())
    finally:
        mm.MONSTERS["Scorpione Gigante"]=prev

def test_defensive_copy():
    item=mm.audit("Sciame di Corvi",catalog())
    item["attributes"]["caratteristiche"]["for"]="99"
    assert mm.audit("Sciame di Corvi",catalog())["attributes"]["caratteristiche"]["for"]=="6"
