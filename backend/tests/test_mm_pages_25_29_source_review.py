"""Protected source-window regression: MM pages 25, 28 and 29."""
from copy import deepcopy
import pytest
from services import mm_pages_25_29_source_review as m

def source():
    return {"logical_source_id":m.SOURCE_ID,"physical_filename":m.FILE,
        "physical_sha256":m.SOURCE_SHA,"physical_pages":m.SOURCE_PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required"}

@pytest.mark.parametrize("name,page,ac,pf,gs",[
    ("Behir",25,"17 (armatura naturale)","168 (16d12 + 64)","11"),
    ("Beholder",28,"18 (armatura naturale)","180 (19d10 + 76)","13"),
    ("Tiranno Della Morte",29,"19 (armatura naturale)","187 (25d10 + 50)","14"),
])
def test_core_source_agreement(name,page,ac,pf,gs):
    result=m.audit_mm_block(name,source(),False,[])
    assert result["page"]==page
    assert result["attributes"]["classe_armatura"]==ac
    assert result["attributes"]["punti_ferita"]==pf
    assert result["attributes"]["grado_sfida"]==gs
    assert result["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert result["writes"]==0

@pytest.mark.parametrize("name",list(m.SPECIES))
def test_monster_duplicates_rejected(name):
    with pytest.raises(ValueError,match="already_present"):
        m.audit_mm_block(name,source(),True,[])
    with pytest.raises(ValueError,match="already_present"):
        m.audit_mm_block(name,source(),False,[{"name":name,"reference_type":"monster"}])

@pytest.mark.parametrize("key,value",[
    ("physical_filename","wrong.pdf"),
    ("physical_sha256","0"*64),
    ("logical_source_id","other"),
    ("source_status","inactive"),
])
def test_catalog_provenance_gate(key,value):
    s=source();s[key]=value
    with pytest.raises(ValueError,match="catalog_source"):
        m.audit_mm_block("Beholder",s,False,[])

@pytest.mark.parametrize("name,field,new_value",[
    ("Behir","hp","169 (16d12 + 65)"),
    ("Beholder","speed","0 m, volare 9 m (fluttuare)"),
    ("Beholder","gs","14"),
    ("Tiranno Della Morte","ac","18 (armatura naturale)"),
])
def test_plausible_wrong_value_blocked(name,field,new_value,monkeypatch):
    altered=deepcopy(m.SPECIES)
    altered[name][field]=new_value
    monkeypatch.setattr(m,"SPECIES",altered)
    with pytest.raises(ValueError,match="sealed_visual"):
        m.audit_mm_block(name,source(),False,[])

def test_snapshot_does_not_mutate_saved_evidence():
    saved=deepcopy(m.SPECIES["Beholder"])
    out=m.audit_mm_block("Beholder",source(),False,[])
    out["attributes"]["caratteristiche"]["int"]="1"
    assert m.SPECIES["Beholder"]==saved
