"""Fail-closed audit for four source-confirmed MM blocks on pages 30–32."""
from copy import deepcopy
import pytest
from services import mm_pages_30_32_source_review as s

def registry():
    return {"logical_source_id":s.SOURCE_ID,"physical_filename":s.FILENAME,
        "physical_sha256":s.SHA256,"physical_pages":s.PAGES,
        "source_role":"authority","source_status":"active",
        "authority_class":"licensed_translation","text_mode":"vision_required"}

@pytest.mark.parametrize("name,page,ca,hp,gs",[
    ("Spettatore",30,"14 (armatura naturale)","39 (6d8 + 12)","3"),
    ("Belva Distorcente",31,"13 (armatura naturale)","85 (10d10 + 30)","3"),
    ("Bugbear",32,"16 (armatura di pelle, scudo)","27 (5d8 + 5)","1"),
    ("Bugbear Capotribù",32,"17 (giaco di maglia, scudo)","65 (10d8 + 20)","3"),
])
def test_exact_original_fields(name,page,ca,hp,gs):
    out=s.audit(name,registry(),False,[])
    assert out["page"]==page
    assert out["attributes"]["classe_armatura"]==ca
    assert out["attributes"]["punti_ferita"]==hp
    assert out["attributes"]["grado_sfida"]==gs
    assert out["writes"]==0

def test_bugbears_are_two_distinct_statblocks_on_page_32():
    a=s.audit("Bugbear",registry(),False,[])
    b=s.audit("Bugbear Capotribù",registry(),False,[])
    assert a["page"]==b["page"]==32 and a["id"]!=b["id"]

@pytest.mark.parametrize("name",list(s.MONSTERS))
def test_duplicate_monster_is_blocked(name):
    with pytest.raises(ValueError,match="duplicate"):
        s.audit(name,registry(),True,[])
    with pytest.raises(ValueError,match="duplicate"):
        s.audit(name,registry(),False,[{"name":name}])

@pytest.mark.parametrize("key,bad",[
    ("physical_sha256","0"*64),
    ("physical_pages",0),
    ("source_status","duplicate"),
    ("logical_source_id","other"),
])
def test_wrong_registered_source_is_blocked(key,bad):
    record=registry();record[key]=bad
    with pytest.raises(ValueError,match="registered_source"):
        s.audit("Bugbear",record,False,[])

@pytest.mark.parametrize("name,key,bad",[
    ("Spettatore","hp","40 (6d8 + 13)"),
    ("Belva Distorcente","gs","4"),
    ("Bugbear","ac","17 (armatura di pelle, scudo)"),
    ("Bugbear Capotribù","speed","12 m"),
])
def test_wrong_but_plausible_value_fails(name,key,bad,monkeypatch):
    items=deepcopy(s.MONSTERS);items[name][key]=bad
    monkeypatch.setattr(s,"MONSTERS",items)
    with pytest.raises(ValueError,match="sealed_original"):
        s.audit(name,registry(),False,[])

def test_no_mutation_of_original_constants():
    before=deepcopy(s.MONSTERS["Spettatore"])
    result=s.audit("Spettatore",registry(),False,[])
    result["attributes"]["caratteristiche"]["for"]="1"
    assert s.MONSTERS["Spettatore"]==before
