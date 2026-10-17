"""Original registered-source audit regressions for three boxed encounters."""
from copy import deepcopy
import hashlib
import pytest
import services.mpmm_matrona_laceratore_abiuratore_review as m
from services.mpmm_matrona_laceratore_abiuratore_review import (
    OWNER,SOURCE,TARGETS,registered_ref,inspect_named_original,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

SYNTHETIC="Synthetic unit-test narrative, not source copyrighted prose."*5

@pytest.fixture(params=list(TARGETS))
def original(request,monkeypatch):
    name=request.param
    spec=TARGETS[name]
    changed=deepcopy(TARGETS)
    changed[name]["raw_sha"]=hashlib.sha256(SYNTHETIC.encode()).hexdigest()
    monkeypatch.setattr(m,"TARGETS",changed)
    return name,{
        "id":spec["id"],"user_id":OWNER,
        "name":name,"source_name":name,"normalized_name":name.casefold(),
        "reference_type":"other","review_status":"verified",
        "review_flags":[],"canonical_id":None,"source_key":SOURCE,
        "source_language":"it","source_text_checksum":spec["checksum"],
        "source_refs":[registered_ref(spec["ref_page"])],
        "attributes":{},"source_attributes":{},"review_corrections":{},
        "full_text":SYNTHETIC,"source_full_text":SYNTHETIC,
    }

def test_original_sources_eligible_without_writes(original):
    name,row=original
    snapshot=deepcopy(row)
    verdict=inspect_named_original(name,row)
    assert verdict["status"]=="eligible_original_boxed_monster"
    assert verdict["writes"]==0
    assert verdict["attrs"]==TARGETS[name]["attrs"]
    assert row==snapshot
    assert not monster_semantic_numeric_flags(verdict["attrs"])

@pytest.mark.parametrize(("field","bad"),[
    ("id","other"),("user_id","wrong"),("name","wrong"),("source_name","wrong"),
    ("normalized_name","wrong"),("reference_type","monster"),
    ("review_status","pending"),("review_flags",["ocr_da_verificare"]),
    ("canonical_id","dup"),("source_key","wrong.pdf"),
    ("source_language","en"),("source_text_checksum","0"*64),
    ("attributes",{"punti_ferita":"247"}),("source_attributes",{"punti_ferita":"247"}),
    ("source_refs",[]),("review_corrections",{"changed":True}),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_snapshot_drift_fails_closed(original,field,bad):
    name,row=original
    row[field]=bad
    with pytest.raises(ValueError):
        inspect_named_original(name,row)

@pytest.mark.parametrize(("key","bad"),[
    ("page",999),("logical_page",999),("filename","wrong.pdf"),
    ("source_status","retired"),("source_role","secondary"),
    ("authority_class","unlicensed"),("logical_source_id","other"),
])
def test_wrong_original_page_or_authority_blocks(original,key,bad):
    name,row=original
    row["source_refs"][0][key]=bad
    with pytest.raises(ValueError):
        inspect_named_original(name,row)

def test_matrona_box_follows_registered_prose_page():
    t=TARGETS["Drow Matrona Madre"]
    assert t["ref_page"]==6 and t["stat_page"]==7

def test_hit_dice_math():
    for spec in TARGETS.values():
        hp,n,faces,mod=spec["dice"]
        assert n*(faces+1)//2+mod==hp
        invalid=dict(spec["attrs"])
        invalid["punti_ferita"]=f"{hp} ({n}d{faces} + {mod+1})"
        assert monster_semantic_numeric_flags(invalid)
