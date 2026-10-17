"""Original Italian MPMM source and math regression tests."""
from copy import deepcopy
import hashlib
import pytest
import services.mpmm_bacio_sacerdote_titivilus_review as m
from services.mpmm_bacio_sacerdote_titivilus_review import (
    OWNER, TARGETS, registered_ref, audit_creature,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE="Purely synthetic test source narrative. " * 9

@pytest.fixture(params=list(TARGETS))
def original(request,monkeypatch):
    name=request.param
    spec=TARGETS[name]
    changed=deepcopy(TARGETS)
    changed[name]["raw_sha"]=hashlib.sha256(FAKE.encode()).hexdigest()
    monkeypatch.setattr(m,"TARGETS",changed)
    return name,{
        "id":spec["id"],"user_id":OWNER,
        "name":name,"source_name":name,"normalized_name":name.casefold(),
        "reference_type":"other","review_status":"verified",
        "review_flags":[],"canonical_id":None,
        "source_key":spec["file"],"source_language":"it",
        "source_text_checksum":spec["checksum"],
        "source_refs":[registered_ref(spec)],
        "attributes":{},"source_attributes":{},"review_corrections":{},
        "full_text":FAKE,"source_full_text":FAKE,
    }

def test_exact_registered_sources_eligible_without_writing(original):
    name,row=original
    original_copy=deepcopy(row)
    out=audit_creature(name,row)
    assert out["status"]=="eligible_separately_named_original_statblock"
    assert out["writes"]==0
    assert out["attrs"]==TARGETS[name]["attrs"]
    assert row==original_copy
    assert not monster_semantic_numeric_flags(out["attrs"])

@pytest.mark.parametrize(("key","bad"),[
    ("id","wrong"),("user_id","wrong"),("name","Other"),
    ("source_name","Other"),("normalized_name","Other"),
    ("reference_type","monster"),("review_status","pending"),
    ("review_flags",["ocr_da_verificare"]),("canonical_id","duplicate"),
    ("source_key","wrong.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),("source_refs",[]),
    ("attributes",{"punti_ferita":"150"}),("source_attributes",{"punti_ferita":"150"}),
    ("review_corrections",{"_source_changed":True}),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_drift_rejected(original,key,bad):
    name,row=original
    row[key]=bad
    with pytest.raises(ValueError):
        audit_creature(name,row)

@pytest.mark.parametrize(("key","bad"),[
    ("page",99),("logical_page",0),("filename","fake.pdf"),
    ("source_role","secondary"),("authority_class","unlicensed"),
    ("logical_source_id","other"),("source_status","retired"),
])
def test_source_authority_page_sealed(original,key,bad):
    name,row=original
    row["source_refs"][0][key]=bad
    with pytest.raises(ValueError):
        audit_creature(name,row)

def test_titivilus_description_page_differs_from_original_statbox():
    spec=TARGETS["Titivilus"]
    assert spec["ref_page"]==55
    assert spec["stat_page"]==56
    assert spec["logical"]==255

def test_original_hit_dice_are_math_consistent():
    for spec in TARGETS.values():
        hp,n,sides,bonus=spec["dice"]
        assert n*(sides+1)//2+bonus==hp
        bad=dict(spec["attrs"])
        bad["punti_ferita"]=f"{hp} ({n}d{sides} + {bonus+1})"
        assert monster_semantic_numeric_flags(bad)
