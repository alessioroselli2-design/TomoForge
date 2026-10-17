"""Fail-closed source and HP numerical regressions for original MPMM monsters."""
import hashlib
from copy import deepcopy
import pytest

import services.mpmm_amnizu_archdruid_chitine_review as m
from services.mpmm_amnizu_archdruid_chitine_review import (
    OWNER,SOURCE,TARGETS,authority,check_independent_statblock,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE="Synthetic test-only creature narrative. "*9

@pytest.fixture(params=list(TARGETS))
def original(request,monkeypatch):
    name=request.param
    spec=TARGETS[name]
    altered=deepcopy(TARGETS)
    altered[name]["raw_sha"]=hashlib.sha256(FAKE.encode()).hexdigest()
    monkeypatch.setattr(m,"TARGETS",altered)
    return name,{
        "id":spec["id"],"user_id":OWNER,
        "name":name,"source_name":name,"normalized_name":name.casefold(),
        "reference_type":"other","review_status":"verified","review_flags":[],
        "canonical_id":None,"source_key":SOURCE,"source_language":"it",
        "source_text_checksum":spec["checksum"],"source_refs":[authority(spec["page"])],
        "attributes":{},"source_attributes":{},"review_corrections":{},
        "full_text":FAKE,"source_full_text":FAKE,
    }

def test_exact_source_allows_read_only(original):
    name,row=original
    saved=deepcopy(row)
    result=check_independent_statblock(name,row)
    assert result["status"]=="eligible_registered_boxed_monster_reclassification"
    assert result["writes"]==0
    assert result["attrs"]==TARGETS[name]["attrs"]
    assert not monster_semantic_numeric_flags(result["attrs"])
    assert row==saved

@pytest.mark.parametrize(("key","bad"),[
    ("id","changed"),("name","Other"),("source_name","Other"),
    ("normalized_name","Other"),("reference_type","monster"),
    ("review_status","needs_review"),("review_flags",["ocr_da_verificare"]),
    ("canonical_id","duplicate"),("source_key","other.pdf"),
    ("source_language","en"),("source_text_checksum","0"*64),
    ("source_refs",[]),("attributes",{"classe_armatura":"14"}),
    ("source_attributes",{"classe_armatura":"14"}),("review_corrections",{"changed":1}),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_mutated_historical_record_blocked(original,key,bad):
    name,row=original
    row[key]=bad
    with pytest.raises(ValueError):
        check_independent_statblock(name,row)

@pytest.mark.parametrize(("key","bad"),[
    ("page",90),("logical_page",90),("filename","wrong.pdf"),
    ("source_role","secondary"),("source_status","retired"),
    ("authority_class","unlicensed"),("logical_source_id","wrong"),
])
def test_wrong_authority_rejected(original,key,bad):
    name,row=original
    row["source_refs"][0][key]=bad
    with pytest.raises(ValueError):
        check_independent_statblock(name,row)

def test_hit_dice_average():
    for spec in TARGETS.values():
        hp,n,sides,bonus=spec["dice"]
        assert n*(sides+1)//2+bonus==hp
        wrong=dict(spec["attrs"])
        wrong["punti_ferita"]=f"{hp} ({n}d{sides} + {bonus+1})"
        assert monster_semantic_numeric_flags(wrong)
