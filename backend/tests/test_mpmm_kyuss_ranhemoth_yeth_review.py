"""Negative source-drift and HP-math regressions for three MPMM monsters."""
import hashlib
from copy import deepcopy
import pytest

import services.mpmm_kyuss_ranhemoth_yeth_review as review
from services.mpmm_kyuss_ranhemoth_yeth_review import (
    TARGETS, OWNER, SOURCE, authority, review_monster_source,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE = "Synthetic test-only narrative, never copied from a licensed book. " * 6


@pytest.fixture(params=list(TARGETS))
def original(request,monkeypatch):
    name=request.param
    t=TARGETS[name]
    clone=deepcopy(TARGETS)
    clone[name]["raw_sha"]=hashlib.sha256(FAKE.encode()).hexdigest()
    monkeypatch.setattr(review,"TARGETS",clone)
    return name,{
        "id":t["id"],"user_id":OWNER,
        "name":name,"source_name":name,"normalized_name":name.casefold(),
        "reference_type":"other","review_status":"needs_review",
        "review_flags":t["flags"],"canonical_id":None,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":t["checksum"],
        "source_refs":[authority(t["page"])],
        "attributes":{},"source_attributes":{},
        "review_corrections":{"_source_changed":True},
        "full_text":FAKE,"source_full_text":FAKE,
    }


def test_positive_original_is_readonly(original):
    name,row=original
    old=deepcopy(row)
    decision=review_monster_source(name,row)
    assert decision["status"]=="eligible_source_locked_monster_reclassification"
    assert decision["writes"]==0
    assert decision["attributes"]==TARGETS[name]["attrs"]
    assert row==old
    assert not monster_semantic_numeric_flags(decision["attributes"])


@pytest.mark.parametrize(("key","invalid"),[
    ("id","other"),("user_id","wrong"),("name","Other"),
    ("source_name","Other"),("normalized_name","wrong"),
    ("reference_type","monster"),("review_status","verified"),
    ("review_flags",["invalid"]),("canonical_id","duplicate"),
    ("source_key","wrong.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),
    ("source_refs",[]),("attributes",{"velocita":"9 m"}),
    ("source_attributes",{"punti_ferita":"76"}),
    ("review_corrections",{}),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_any_historical_source_drift_blocks(original,key,invalid):
    name,row=original
    row[key]=invalid
    with pytest.raises(ValueError):
        review_monster_source(name,row)


@pytest.mark.parametrize(("key","invalid"),[
    ("page",100),("logical_page",300),("filename","wrong.pdf"),
    ("source_role","secondary"),("logical_source_id","unknown"),
    ("source_status","inactive"),("authority_class","unlicensed"),
    ("ruleset","2024"),
])
def test_nearby_or_wrong_source_statblocks_not_accepted(original,key,invalid):
    name,row=original
    row["source_refs"][0][key]=invalid
    with pytest.raises(ValueError):
        review_monster_source(name,row)


def test_duplicate_source_ref_and_wrong_name_fail(original):
    name,row=original
    row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        review_monster_source(name,row)
    with pytest.raises(ValueError):
        review_monster_source("Unregistered",row)


def test_hit_dice_average_matches_original():
    for spec in TARGETS.values():
        hp,count,faces,bonus=spec["dice"]
        assert count*(faces+1)//2+bonus==hp
        altered=dict(spec["attrs"])
        altered["punti_ferita"]=f"{hp} ({count}d{faces} + {bonus+1})"
        assert monster_semantic_numeric_flags(altered)
