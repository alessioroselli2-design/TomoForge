"""Fail-closed source and continuity-marker regressions for Troll Feroce."""
from copy import deepcopy
import hashlib
import pytest
import services.mpmm_troll_feroce_source_review as audit
from services.mpmm_troll_feroce_source_review import (
 ID, NAME, OWNER, SOURCE, CHECKSUM, AUTHORITY, ATTRIBUTES, inspect_troll_feroce
)

RAW = "Synthetic unit-test monster prose; this is not an original statblock." * 5


@pytest.fixture
def record(monkeypatch):
    monkeypatch.setattr(audit, "RAW_SHA", hashlib.sha256(RAW.encode()).hexdigest())
    return {
        "id":ID,"name":NAME,"source_name":NAME,
        "normalized_name":NAME.casefold(),"user_id":OWNER,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":CHECKSUM,"source_refs":[deepcopy(AUTHORITY)],
        "reference_type":"ability","review_status":"needs_review",
        "review_flags":["sezione_potenzialmente_continua"],
        "canonical_id":None,"attributes":{},"source_attributes":{},
        "review_corrections":{"_source_changed":True},
        "full_text":RAW,"source_full_text":RAW,
    }


def test_registered_source_eligible_no_writes(record):
    before=deepcopy(record)
    verdict=inspect_troll_feroce(record)
    assert verdict["status"]=="eligible_exact_source_monster_reclassification"
    assert verdict["writes"]==0
    assert verdict["attributes"]==ATTRIBUTES
    assert record==before


@pytest.mark.parametrize(("key","bad"),[
    ("id","wrong"),("name","Wrong"),("source_name","Wrong"),
    ("normalized_name","wrong"),("user_id","wrong"),
    ("source_key","wrong.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),("source_refs",[]),
    ("reference_type","monster"),("review_status","verified"),
    ("review_flags",[]),("review_flags",["ocr_da_verificare"]),
    ("canonical_id","dup"),("attributes",{"punti_ferita":"172"}),
    ("source_attributes",{"punti_ferita":"172"}),
    ("review_corrections",{}),("full_text","different"),
    ("source_full_text","different"),
])
def test_source_snapshot_mutation_rejected(record,key,bad):
    record[key]=bad
    with pytest.raises(ValueError):
        inspect_troll_feroce(record)


@pytest.mark.parametrize(("key","bad"),[
    ("page",60),("logical_page",260),("filename","wrong.pdf"),
    ("source_role","secondary"),("source_status","retired"),
    ("logical_source_id","other"),("authority_class","unlicensed"),
])
def test_wrong_statblock_page_and_authority_rejected(record,key,bad):
    record["source_refs"][0][key]=bad
    with pytest.raises(ValueError):
        inspect_troll_feroce(record)


def test_duplicate_source_refs_rejected(record):
    record["source_refs"].append(deepcopy(record["source_refs"][0]))
    with pytest.raises(ValueError):
        inspect_troll_feroce(record)
