"""Fail-closed original-source numeric/provenance regressions for four MPMM monsters."""
import hashlib
from copy import deepcopy
import pytest
import services.mpmm_next_four_source_review as mod
from services.mpmm_next_four_source_review import OWNER,SRC,TARGETS,authority,audit_mpmm_encounter
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE_RAW="Synthetic regression description; no copyrighted game prose. "*6


@pytest.fixture(params=list(TARGETS))
def original(request,monkeypatch):
    name=request.param
    t=TARGETS[name]
    copy=deepcopy(TARGETS)
    copy[name]["raw_sha256"]=hashlib.sha256(FAKE_RAW.encode()).hexdigest()
    monkeypatch.setattr(mod,"TARGETS",copy)
    row={
        "id":t["id"],"user_id":OWNER,"name":name,"source_name":name,
        "normalized_name":name.casefold(),"reference_type":"other",
        "review_status":"needs_review","review_flags":[],
        "source_language":"it","source_key":SRC,"canonical_id":None,
        "source_text_checksum":t["checksum"],"attributes":{},
        "source_attributes":{},"review_corrections":{"_source_changed":True},
        "source_refs":[authority(t["page"],t["logical_page"])],
        "full_text":FAKE_RAW,"source_full_text":FAKE_RAW,
    }
    return name,row


def test_exact_row_eligible_and_readonly(original):
    name,row=original
    before=deepcopy(row)
    result=audit_mpmm_encounter(name,row)
    assert result["status"]=="eligible_original_source_reclassification"
    assert result["writes"]==0
    assert result["attributes"]==TARGETS[name]["attrs"]
    assert row==before
    assert not monster_semantic_numeric_flags(result["attributes"])


@pytest.mark.parametrize(("field","bad"),[
    ("id","wrong"),("name","Other"),("normalized_name","other"),
    ("source_name","Other"),("reference_type","monster"),
    ("review_status","verified"),("review_flags",["ocr_da_verificare"]),
    ("canonical_id","duplicate"),("source_key","wrong.pdf"),
    ("source_text_checksum","0"*64),("attributes",{"punti_ferita":"52"}),
    ("source_attributes",{"punti_ferita":"52"}),("review_corrections",{}),
    ("source_refs",[]),("full_text","different"),("source_full_text","different"),
])
def test_independent_source_drift_rejected(original,field,bad):
    name,row=original;row[field]=bad
    with pytest.raises(ValueError):
        audit_mpmm_encounter(name,row)


@pytest.mark.parametrize(("field","bad"),[
    ("page",999),("logical_page",999),("filename","wrong"),
    ("logical_source_id","other"),("source_role","secondary"),
    ("authority_class","unlicensed"),("source_status","inactive"),
])
def test_registered_page_and_role_are_strict(original,field,bad):
    name,row=original;row["source_refs"][0][field]=bad
    with pytest.raises(ValueError):
        audit_mpmm_encounter(name,row)


def test_multiple_authority_refs_rejected(original):
    name,row=original;row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        audit_mpmm_encounter(name,row)


def test_invalid_dice_tuple_rejected():
    for spec in TARGETS.values():
        hp,n,die,bonus=spec["dice"]
        assert (n*(die+1))//2+bonus==hp
        assert monster_semantic_numeric_flags(
            {**spec["attrs"],"punti_ferita":f"{hp} ({n}d{die} + {bonus+1})"}
        )
