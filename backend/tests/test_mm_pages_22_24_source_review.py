"""Fail-closed source coverage: three source-checked blocks on MM p22-24."""
from copy import deepcopy
import pytest
from services import mm_pages_22_24_source_review as m

def source():
    return {
        "logical_source_id":m.SOURCE_ID, "physical_filename":m.SOURCE_FILE,
        "physical_sha256":m.SOURCE_SHA, "physical_pages":m.SOURCE_PAGES,
        "source_status":"active", "source_role":"authority",
        "authority_class":"licensed_translation", "text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","ca","hp","gs"),[
    ("Azer",22,"17 (armatura naturale, scudo)","39 (6d8 + 12)","2"),
    ("Banshee",23,"12","58 (13d8)","4"),
    ("Basilisco",24,"15 (armatura naturale)","52 (8d8 + 16)","3"),
])
def test_exact_original_statblock(name,page,ca,hp,gs):
    result=m.audit_source(name,False,[],source())
    assert result["page"]==page
    assert result["attributes"]["classe_armatura"]==ca
    assert result["attributes"]["punti_ferita"]==hp
    assert result["attributes"]["grado_sfida"]==gs
    assert result["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert result["writes"]==0

@pytest.mark.parametrize("name",list(m.MONSTERS))
def test_collisions_fail_closed(name):
    with pytest.raises(ValueError,match="collision"):
        m.audit_source(name,True,[],source())
    with pytest.raises(ValueError,match="collision"):
        m.audit_source(name,False,[{"id":"existing"}],source())

@pytest.mark.parametrize(("field","value"),[
    ("physical_filename","altered.pdf"),
    ("physical_sha256","0"*64),
    ("physical_pages",150),
    ("source_status","duplicate"),
    ("authority_class","unknown"),
])
def test_source_registry_mismatch(field,value):
    s=source();s[field]=value
    with pytest.raises(ValueError,match="source_registry"):
        m.audit_source("Azer",False,[],s)

@pytest.mark.parametrize(("name","field","value"),[
    ("Azer","hp","40 (6d8 + 13)"),
    ("Azer","ac","18 (armatura naturale, scudo)"),
    ("Banshee","speed","0 m, volare 15 m (fluttuare)"),
    ("Basilisco","gs","4"),
    ("Basilisco","kind","Mostruosità Grande"),
])
def test_plausible_but_wrong_values_rejected(monkeypatch,name,field,value):
    specs=deepcopy(m.MONSTERS)
    specs[name][field]=value
    monkeypatch.setattr(m,"MONSTERS",specs)
    with pytest.raises(ValueError,match="source_statblock_drift"):
        m.audit_source(name,False,[],source())

def test_returned_attributes_are_immutable_snapshot():
    before=deepcopy(m.MONSTERS["Banshee"])
    result=m.audit_source("Banshee",False,[],source())
    result["attributes"]["caratteristiche"]["for"]="20"
    assert m.MONSTERS["Banshee"]==before
