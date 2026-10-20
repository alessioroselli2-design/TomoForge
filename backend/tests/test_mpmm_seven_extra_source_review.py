"""Fail-closed exact source and numeric tests for seven MPMM creatures."""
import hashlib
from copy import deepcopy
import pytest
import services.mpmm_seven_extra_source_review as review
from services.mpmm_seven_extra_source_review import TARGETS,OWNER,authority,part_filename,source_audit
from services.ocr_semantic_gates import monster_semantic_numeric_flags

SYNTHETIC="Synthetic unit-test source placeholder, not original copyrighted text. "*5

@pytest.fixture(params=list(TARGETS))
def record(request,monkeypatch):
    name=request.param
    spec=TARGETS[name]
    copy=deepcopy(TARGETS)
    copy[name]["raw"]=hashlib.sha256(SYNTHETIC.encode()).hexdigest()
    monkeypatch.setattr(review,"TARGETS",copy)
    row={"id":spec["id"],"user_id":OWNER,"name":name,"source_name":name,
         "normalized_name":name.casefold(),"reference_type":spec["type"],
         "review_status":spec["status"],"review_flags":spec["flags"],
         "canonical_id":None,"source_key":part_filename(spec["part"]),
         "source_language":"it","source_text_checksum":spec["checksum"],
         "source_refs":[authority(spec)],"attributes":{},"source_attributes":{},
         "review_corrections":spec["corr"],
         "full_text":SYNTHETIC,"source_full_text":SYNTHETIC}
    return name,row

def test_original_row_matches_and_is_readonly(record):
    name,row=record
    before=deepcopy(row)
    report=source_audit(name,row)
    assert report["status"]=="eligible_original_independent_boxed_monster"
    assert report["stats"]==TARGETS[name]["stats"]
    assert report["writes"]==0
    assert row==before
    assert not monster_semantic_numeric_flags(report["stats"])

@pytest.mark.parametrize(("field","bad"),[
    ("id","wrong"),("name","wrong"),("source_name","wrong"),
    ("normalized_name","wrong"),("user_id","other"),
    ("reference_type","monster"),("review_status","pending"),
    ("review_flags",["wrong"]),("canonical_id","duplicate"),
    ("source_key","wrong.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),
    ("source_refs",[]),("attributes",{"punti_ferita":"216"}),
    ("source_attributes",{"classe_armatura":"19"}),
    ("review_corrections",{"untracked":True}),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_original_source_drift_never_accepted(record,field,bad):
    name,row=record
    row[field]=bad
    with pytest.raises(ValueError):
        source_audit(name,row)

@pytest.mark.parametrize(("field","bad"),[
    ("page",1),("filename","wrong.pdf"),("logical_page",1000),
    ("logical_source_id","wrong"),("source_role","secondary"),
    ("authority_class","unlicensed"),("source_status","retired"),
])
def test_other_pdf_page_or_source_denied(record,field,bad):
    name,row=record
    row["source_refs"][0][field]=bad
    with pytest.raises(ValueError):
        source_audit(name,row)

def test_hit_dice_math_for_all_seven():
    for spec in TARGETS.values():
        hp,n,d,b=spec["dice"]
        assert n*(d+1)//2+b==hp
        assert monster_semantic_numeric_flags(
            {**spec["stats"],"punti_ferita":f"{hp} ({n}d{d} + {b+1})"}
        )

def test_hutijin_original_source_narrative_and_box_page_distinction():
    s=TARGETS["Hutijin"]
    assert s["page"]==50 and s["box"]==51
