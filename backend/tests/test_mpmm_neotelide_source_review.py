"""Source-locked read-only Neotelide reviews fail closed on any change."""
from copy import deepcopy
import hashlib
import pytest
import services.mpmm_neotelide_source_review as mod
from services.mpmm_neotelide_source_review import ID, OWNER, NAME, SOURCE, CHECKSUM, REF, ATTRS, assess_neotelide

TEXT="Synthetic test evidence rather than reproduced source pages. "*5

@pytest.fixture
def original(monkeypatch):
    monkeypatch.setattr(mod,"SOURCE_SHA",hashlib.sha256(TEXT.encode()).hexdigest())
    return {
        "id":ID,"user_id":OWNER,"name":NAME,"source_name":NAME,
        "normalized_name":NAME.casefold(),"reference_type":"other",
        "review_status":"needs_review",
        "review_flags":["sezione_potenzialmente_continua"],
        "canonical_id":None,"source_key":SOURCE,"source_language":"it",
        "source_text_checksum":CHECKSUM,"source_refs":[deepcopy(REF)],
        "review_corrections":{"_source_changed":True},
        "attributes":{},"source_attributes":{},
        "full_text":TEXT,"source_full_text":TEXT,
    }

def test_eligible_zero_writes(original):
    before=deepcopy(original)
    result=assess_neotelide(original)
    assert result["status"]=="eligible_original_named_statblock"
    assert result["writes"]==0
    assert result["attributes"]==ATTRS
    assert original==before

@pytest.mark.parametrize(("key","bad"),[
    ("id","changed"),("user_id","changed"),("name","wrong"),
    ("source_name","wrong"),("normalized_name","wrong"),
    ("reference_type","monster"),("review_status","verified"),
    ("review_flags",[]),("canonical_id","other"),
    ("source_key","wrong.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),("attributes",{"punti_ferita":"232"}),
    ("source_attributes",{"punti_ferita":"232"}),
    ("review_corrections",{}),("source_refs",[]),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_original_snapshot_drift_rejected(original,key,bad):
    original[key]=bad
    with pytest.raises(ValueError):
        assess_neotelide(original)

@pytest.mark.parametrize(("key","bad"),[
    ("page",2),("logical_page",202),("filename","wrong"),
    ("logical_source_id","other"),("source_status","inactive"),
    ("source_role","secondary"),("authority_class","unlicensed"),
])
def test_provenance_not_reused_from_neighbor(original,key,bad):
    original["source_refs"][0][key]=bad
    with pytest.raises(ValueError):
        assess_neotelide(original)

def test_duplicate_authority_rejected(original):
    original["source_refs"].append(deepcopy(original["source_refs"][0]))
    with pytest.raises(ValueError):
        assess_neotelide(original)
