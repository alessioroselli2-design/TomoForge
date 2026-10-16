"""Original source drift and dice-average regression for four MPMM creatures."""
from copy import deepcopy
import hashlib
import pytest
import services.mpmm_four_named_statblocks_review as review
from services.mpmm_four_named_statblocks_review import TARGETS, OWNER, FILE, authority, validate_record
from services.ocr_semantic_gates import monster_semantic_numeric_flags

DUMMY="Synthetic test-only description; not any publisher-protected content. "*5

@pytest.fixture(params=list(TARGETS))
def record(request,monkeypatch):
    name=request.param
    t=TARGETS[name]
    copied=deepcopy(TARGETS)
    copied[name]["raw"]=hashlib.sha256(DUMMY.encode()).hexdigest()
    monkeypatch.setattr(review,"TARGETS",copied)
    return name,{
        "id":t["id"],"user_id":OWNER,"name":name,"source_name":name,
        "normalized_name":name.casefold(),"reference_type":t["type"],
        "review_status":"needs_review","review_flags":t["flag"],
        "canonical_id":None,"source_key":FILE,"source_language":"it",
        "source_text_checksum":t["checksum"],"source_refs":[authority(t["page"])],
        "attributes":{},"source_attributes":{},"review_corrections":t["corr"],
        "full_text":DUMMY,"source_full_text":DUMMY,
    }

def test_exact_source_is_readonly_eligible(record):
    name,row=record
    original=deepcopy(row)
    outcome=validate_record(name,row)
    assert outcome["writes"]==0
    assert outcome["status"]=="eligible_exact_original_source_reclassification"
    assert outcome["attributes"]==TARGETS[name]["attrs"]
    assert row==original
    assert not monster_semantic_numeric_flags(outcome["attributes"])

@pytest.mark.parametrize(("field","bad"),[
    ("id","changed"),("name","wrong"),("source_name","wrong"),
    ("normalized_name","wrong"),("user_id","wrong"),
    ("reference_type","monster"),("review_status","verified"),
    ("review_flags",["ocr_da_verificare"]),("canonical_id","other"),
    ("source_key","wrong.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),("source_refs",[]),
    ("attributes",{"classe_armatura":"14"}),("source_attributes",{"punti_ferita":"22"}),
    ("review_corrections",{}),("full_text","modified"),("source_full_text","modified"),
])
def test_any_original_row_change_blocks(record,field,bad):
    name,row=record
    row[field]=bad
    with pytest.raises(ValueError):
        validate_record(name,row)

@pytest.mark.parametrize(("field","bad"),[
    ("page",1),("logical_page",201),("source_role","secondary"),
    ("logical_source_id","wrong"),("source_status","retired"),
    ("authority_class","unlicensed"),("filename","wrong.pdf"),
])
def test_wrong_source_page_or_authority_fails(record,field,bad):
    name,row=record
    row["source_refs"][0][field]=bad
    with pytest.raises(ValueError):
        validate_record(name,row)

def test_hp_math_for_all_original_statblocks():
    for t in TARGETS.values():
        hp,n,d,b=t["dice"]
        assert n*(d+1)//2+b==hp
        alternate={**t["attrs"],"punti_ferita":f"{hp} ({n}d{d} + {b+1})"}
        assert monster_semantic_numeric_flags(alternate)
