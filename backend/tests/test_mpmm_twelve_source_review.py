"""No-write fail-closed source review of twelve independent MPMM statblocks."""
import hashlib
from copy import deepcopy

import pytest

import services.mpmm_twelve_source_review as mod
from services.mpmm_twelve_source_review import (
    TARGETS, OWNER, FILE, authority, audit_existing_monster,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

SYNTHETIC="Synthetic unit test description, never publisher source prose. " * 6


@pytest.fixture(params=list(TARGETS))
def row(request, monkeypatch):
    name=request.param
    t=TARGETS[name]
    specs=deepcopy(TARGETS)
    specs[name]["raw"]=hashlib.sha256(SYNTHETIC.encode()).hexdigest()
    monkeypatch.setattr(mod,"TARGETS",specs)
    original={
        "id":t["id"],"name":name,"source_name":name,
        "normalized_name":t["normalized"],"user_id":OWNER,
        "reference_type":t["type"],"review_status":t["status"],
        "review_flags":t["flags"],"canonical_id":None,
        "source_key":FILE,"source_language":"it",
        "source_text_checksum":t["checksum"],
        "attributes":deepcopy(t["attrs"]),
        "source_attributes":deepcopy(t["source_attrs"]),
        "review_corrections":deepcopy(t["corr"]),
        "source_refs":[authority(t["page"])],
        "full_text":SYNTHETIC,"source_full_text":SYNTHETIC,
    }
    return name,original


def test_positive_exact_original_is_readonly(row):
    name,data=row
    before=deepcopy(data)
    verdict=audit_existing_monster(name,data)
    assert verdict["status"]=="eligible_independent_source_monster_review"
    assert verdict["proposed_attributes"]==TARGETS[name]["proposed"]
    assert verdict["writes"]==0
    assert data==before
    assert not monster_semantic_numeric_flags(TARGETS[name]["proposed"])


@pytest.mark.parametrize(("field","bad"),[
    ("id","changed"),("user_id","bad-user"),("name","wrong"),
    ("source_name","wrong"),("normalized_name","wrong"),
    ("reference_type","monster"),("review_status","pending"),
    ("review_flags",["other"]),("canonical_id","duplicate"),
    ("source_key","wrong.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),("source_refs",[]),
    ("attributes",{"punti_ferita":"invalid"}),
    ("source_attributes",{"punti_ferita":"invalid"}),
    ("review_corrections",{"unexpected":True}),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_any_registered_source_drift_fails_closed(row,field,bad):
    name,data=row
    data[field]=bad
    if data["review_status"]=="pending" and TARGETS[name]["status"]=="pending":
        pytest.skip("test mutation must differ from original")
    with pytest.raises(ValueError):
        audit_existing_monster(name,data)


@pytest.mark.parametrize(("field","bad"),[
    ("page",99),("logical_page",199),("filename","wrong.pdf"),
    ("logical_source_id","wrong"),("ruleset","2024"),
    ("source_status","inactive"),("source_role","secondary"),
    ("authority_class","unlicensed"),
])
def test_wrong_book_or_page_rejected(row,field,bad):
    name,data=row
    data["source_refs"][0][field]=bad
    if data["source_refs"][0]==authority(TARGETS[name]["page"]):
        pytest.skip("mutation equals expected authority")
    with pytest.raises(ValueError):
        audit_existing_monster(name,data)


def test_dice_consistency_for_every_original():
    for t in TARGETS.values():
        hp,num,faces,bonus=t["dice"]
        assert num*(faces+1)//2+bonus==hp
        mutated={**t["proposed"],"punti_ferita":f"{hp} ({num}d{faces} + {bonus+1})"}
        assert monster_semantic_numeric_flags(mutated)


def test_wrong_entity_never_eligible(row):
    _,data=row
    with pytest.raises(ValueError):
        audit_existing_monster("unregistered",data)
