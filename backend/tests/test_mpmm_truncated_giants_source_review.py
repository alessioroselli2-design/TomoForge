"""Fail-closed original source checks for two separately named giant statblocks."""
from copy import deepcopy
import hashlib
import pytest
import services.mpmm_truncated_giants_source_review as m
from services.mpmm_truncated_giants_source_review import (
    OWNER,TARGETS,authority,inspect_giant,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE="Synthetic original-source excerpt for tests only."*6

@pytest.fixture(params=list(TARGETS))
def original(request,monkeypatch):
    name=request.param
    spec=TARGETS[name]
    clone=deepcopy(TARGETS)
    clone[name]["raw_sha"]=hashlib.sha256(FAKE.encode()).hexdigest()
    monkeypatch.setattr(m,"TARGETS",clone)
    return name,{
        "id":spec["id"],"user_id":OWNER,
        "name":spec["old_name"],"source_name":spec["old_name"],
        "normalized_name":spec["old_name"].casefold(),
        "reference_type":"other","review_status":"needs_review",
        "review_flags":[],"canonical_id":None,"source_key":spec["file"],
        "source_language":"it","source_text_checksum":spec["checksum"],
        "source_refs":[authority(spec)],"attributes":{},"source_attributes":{},
        "review_corrections":{"_source_changed":True},
        "full_text":FAKE,"source_full_text":FAKE,
    }

def test_original_giant_review_never_writes(original):
    name,row=original
    saved=deepcopy(row)
    result=inspect_giant(name,row)
    assert result["status"]=="eligible_full_title_original_giant_monster"
    assert result["writes"]==0
    assert result["correct_name"]==name
    assert row==saved
    assert not monster_semantic_numeric_flags(result["attrs"])

@pytest.mark.parametrize(("field","invalid"),[
    ("id","other"),("user_id","other"),
    ("name","other"),("source_name","other"),
    ("normalized_name","wrong"),
    ("reference_type","monster"),("review_status","verified"),
    ("review_flags",["ocr_da_verificare"]),("canonical_id","dup"),
    ("source_key","other.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),("source_refs",[]),
    ("attributes",{"punti_ferita":"230"}),
    ("source_attributes",{"punti_ferita":"230"}),
    ("review_corrections",{}),("full_text","changed"),("source_full_text","changed"),
])
def test_any_source_snapshot_drift_blocks(original,field,invalid):
    name,row=original
    row[field]=invalid
    with pytest.raises(ValueError):
        inspect_giant(name,row)

@pytest.mark.parametrize(("field","invalid"),[
    ("page",4),("logical_page",4),
    ("filename","wrong.pdf"),("source_role","secondary"),
    ("source_status","retired"),("logical_source_id","wrong"),
    ("authority_class","unlicensed"),
])
def test_wrong_source_authority_blocks(original,field,invalid):
    name,row=original
    row["source_refs"][0][field]=invalid
    with pytest.raises(ValueError):
        inspect_giant(name,row)

def test_dice_average_for_each_named_original():
    for spec in TARGETS.values():
        hp,n,die,bonus=spec["dice"]
        assert n*(die+1)//2+bonus==hp
        invalid=dict(spec["attrs"])
        invalid["punti_ferita"]=f"{hp} ({n}d{die} + {bonus+1})"
        assert monster_semantic_numeric_flags(invalid)
