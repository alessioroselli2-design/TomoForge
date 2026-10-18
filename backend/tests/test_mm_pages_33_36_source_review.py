"""Protected audit of four independent statblocks on MM source p33–36."""
from copy import deepcopy
import pytest
from services import mm_pages_33_36_source_review as s

def source():
    return {
        "logical_source_id":s.SOURCE_ID,
        "physical_filename":s.FILENAME,
        "physical_sha256":s.SHA,
        "physical_pages":s.NUM_PAGES,
        "source_status":"active",
        "source_role":"authority",
        "authority_class":"licensed_translation",
        "text_mode":"vision_required",
    }

@pytest.mark.parametrize("name,page,ca,hp,gs",[
    ("Bulette",33,"17 (armatura naturale)","94 (9d10 + 45)","5"),
    ("Bullywug",34,"15 (armatura di pelle, scudo)","11 (2d8 + 2)","1/4"),
    ("Cacciatore Invisibile",35,"14","104 (16d8 + 32)","6"),
    ("Cambion",36,"19 (corazza di scaglie)","82 (11d8 + 33)","5"),
])
def test_exact_original_statblocks(name,page,ca,hp,gs):
    out=s.audit(name,source(),False,[])
    assert out["page"]==page
    assert out["attributes"]["classe_armatura"]==ca
    assert out["attributes"]["punti_ferita"]==hp
    assert out["attributes"]["grado_sfida"]==gs
    assert out["writes"]==0

@pytest.mark.parametrize("name",list(s.MONSTERS))
def test_verified_monster_collision_fail_closed(name):
    with pytest.raises(ValueError,match="monster_collision"):
        s.audit(name,source(),True,[])
    with pytest.raises(ValueError,match="monster_collision"):
        s.audit(name,source(),False,[{"reference_type":"monster"}])

@pytest.mark.parametrize("field,value",[
    ("physical_sha256","0"*64),
    ("logical_source_id","wrong"),
    ("source_status","inactive"),
    ("physical_pages",150),
])
def test_source_catalog_mismatch(field,value):
    altered=source();altered[field]=value
    with pytest.raises(ValueError,match="registered_source"):
        s.audit("Bulette",altered,False,[])

@pytest.mark.parametrize("name,field,value",[
    ("Bulette","hp","95 (9d10 + 46)"),
    ("Bullywug","gs","1/2"),
    ("Cacciatore Invisibile","speed","15 m, volare 18 m (fluttuare)"),
    ("Cambion","ac","18 (corazza di scaglie)"),
])
def test_plausible_corruption_cannot_pass(name,field,value,monkeypatch):
    changed=deepcopy(s.MONSTERS);changed[name][field]=value
    monkeypatch.setattr(s,"MONSTERS",changed)
    with pytest.raises(ValueError,match="source_core_checksum"):
        s.audit(name,source(),False,[])

def test_saved_source_not_mutated():
    original=deepcopy(s.MONSTERS["Cambion"])
    out=s.audit("Cambion",source(),False,[])
    out["attributes"]["caratteristiche"]["for"]="1"
    assert s.MONSTERS["Cambion"]==original
