"""Historical identity/provenance and math regressions for Yagnoloth."""
from copy import deepcopy
import hashlib
import pytest
import services.mpmm_yagnoloth_source_review as check
from services.mpmm_yagnoloth_source_review import NAME,ID,OWNER,SOURCE,CHECKSUM,REF,ATTRS,review_yagnoloth_source
from services.ocr_semantic_gates import monster_semantic_numeric_flags

RAW="Unit test's synthetic text; not reproduced licensed publisher prose. "*6

@pytest.fixture
def record(monkeypatch):
    monkeypatch.setattr(check,"RAW_SHA",hashlib.sha256(RAW.encode()).hexdigest())
    return {
        "id":ID,"user_id":OWNER,"name":NAME,"source_name":NAME,
        "normalized_name":NAME.casefold(),"reference_type":"other",
        "review_status":"needs_review","review_flags":[],
        "canonical_id":None,"source_key":SOURCE,"source_language":"it",
        "source_text_checksum":CHECKSUM,"source_refs":[deepcopy(REF)],
        "attributes":{},"source_attributes":{},
        "review_corrections":{"_source_changed":True},
        "full_text":RAW,"source_full_text":RAW,
    }

def test_positive_exact_original_no_writes(record):
    before=deepcopy(record)
    verdict=review_yagnoloth_source(record)
    assert verdict["status"]=="eligible_original_source_monster_reclassification"
    assert verdict["writes"]==0 and verdict["attributes"]==ATTRS
    assert record==before

@pytest.mark.parametrize(("field","bad"),[
    ("id","wrong"),("user_id","wrong"),("name","wrong"),
    ("source_name","wrong"),("normalized_name","wrong"),
    ("reference_type","monster"),("review_status","verified"),
    ("review_flags",["ocr_da_verificare"]),("canonical_id","dup"),
    ("source_key","wrong.pdf"),("source_text_checksum","0"*64),
    ("source_refs",[]),("attributes",{"punti_ferita":"147"}),
    ("source_attributes",{"punti_ferita":"147"}),("review_corrections",{}),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_any_original_drift_fails_closed(record,field,bad):
    record[field]=bad
    with pytest.raises(ValueError):
        review_yagnoloth_source(record)

@pytest.mark.parametrize(("field","bad"),[
    ("page",71),("logical_page",271),("filename","other.pdf"),
    ("logical_source_id","other"),("source_role","secondary"),
    ("authority_class","unlicensed"),("source_status","inactive"),
])
def test_wrong_source_authority_rejected(record,field,bad):
    record["source_refs"][0][field]=bad
    with pytest.raises(ValueError):
        review_yagnoloth_source(record)

def test_hp_math_is_sealed():
    assert not monster_semantic_numeric_flags(ATTRS)
    assert monster_semantic_numeric_flags({**ATTRS, "punti_ferita":"147 (14d10 + 71)"})
