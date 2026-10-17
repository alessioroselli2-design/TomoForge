"""Read-only source-regression tests for MPMM separate mage statblocks."""
from copy import deepcopy
import hashlib
import pytest
import services.mpmm_evocatore_necromante_review as m
from services.mpmm_evocatore_necromante_review import (
    OWNER,SOURCE,TARGETS,authority,verify_named_boxed_mage,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE="Synthetic fictional testing narrative."*8

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
        "source_text_checksum":spec["checksum"],"source_refs":[authority()],
        "attributes":{},"source_attributes":{},"review_corrections":{},
        "full_text":FAKE,"source_full_text":FAKE,
    }

def test_original_sealed_rows_valid_read_only(original):
    name,row=original
    saved=deepcopy(row)
    result=verify_named_boxed_mage(name,row)
    assert result["status"]=="eligible_independent_original_mage_monster"
    assert result["writes"]==0
    assert result["attributes"]==TARGETS[name]["attrs"]
    assert not monster_semantic_numeric_flags(result["attributes"])
    assert row==saved

@pytest.mark.parametrize(("field","bad"),[
    ("id","wrong"),("user_id","wrong"),("name","wrong"),
    ("source_name","wrong"),("normalized_name","wrong"),
    ("reference_type","monster"),("review_status","pending"),
    ("review_flags",["ocr_da_verificare"]),("canonical_id","dup"),
    ("source_key","wrong.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),("source_refs",[]),
    ("attributes",{"punti_ferita":"58"}),("source_attributes",{"punti_ferita":"58"}),
    ("review_corrections",{"something":True}),("full_text","changed"),
    ("source_full_text","changed"),
])
def test_every_source_drift_blocks(original,field,bad):
    name,row=original
    row[field]=bad
    with pytest.raises(ValueError):
        verify_named_boxed_mage(name,row)

@pytest.mark.parametrize(("field","bad"),[
    ("page",70),("logical_page",170),("filename","other.pdf"),
    ("source_role","secondary"),("source_status","inactive"),
    ("authority_class","unlicensed"),("logical_source_id","other"),
])
def test_authority_not_replaced_with_statblock_page(original,field,bad):
    name,row=original
    row["source_refs"][0][field]=bad
    with pytest.raises(ValueError):
        verify_named_boxed_mage(name,row)

def test_distinct_registered_prose_and_statblock_pages():
    assert TARGETS["Mago Evocatore"]["stat_page"]==70
    assert TARGETS["Mago Necromante"]["stat_page"]==73
    assert all(x["ref_page"]==68 for x in TARGETS.values())

def test_original_dice_math():
    for spec in TARGETS.values():
        hp,n,sides,bonus=spec["dice"]
        assert n*(sides+1)//2+bonus==hp
        wrong=dict(spec["attrs"])
        wrong["punti_ferita"]=f"{hp} ({n}d{sides} + {bonus+1})"
        assert monster_semantic_numeric_flags(wrong)
