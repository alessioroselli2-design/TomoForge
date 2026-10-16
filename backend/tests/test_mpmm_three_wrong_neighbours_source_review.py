"""Protect verified MPMM records from neighbor-stat mixups and drift."""
import hashlib
from copy import deepcopy
import pytest
import services.mpmm_three_wrong_neighbours_source_review as svc
from services.mpmm_three_wrong_neighbours_source_review import TARGETS,SOURCE,USER,authority,audit_wrong_neighbor
from services.ocr_semantic_gates import monster_semantic_numeric_flags

TEXT="Synthetic nonpublisher data to test original source seals. "*7


@pytest.fixture(params=list(TARGETS))
def original(request,monkeypatch):
    name=request.param
    spec=TARGETS[name]
    test_specs=deepcopy(TARGETS)
    test_specs[name]["raw_sha"]=hashlib.sha256(TEXT.encode()).hexdigest()
    monkeypatch.setattr(svc,"TARGETS",test_specs)
    row={
        "id":spec["id"],"user_id":USER,"name":name,"source_name":name,
        "normalized_name":name.casefold().replace("'"," "),
        "reference_type":"monster","review_status":"verified",
        "review_flags":[],"canonical_id":None,
        "source_key":SOURCE,"source_language":"it",
        "source_text_checksum":spec["checksum"],
        "source_refs":[authority(i) for i in spec["pages"]],
        "attributes":deepcopy(spec["original_attrs"]),
        "source_attributes":deepcopy(spec["source_attrs"]),
        "review_corrections":deepcopy(spec["corrections"]),
        "full_text":TEXT,"source_full_text":TEXT,
    }
    return name,row


def test_read_only_exact_old_state_eligible(original):
    name,row=original
    before=deepcopy(row)
    verdict=audit_wrong_neighbor(name,row)
    assert verdict["status"]=="eligible_verified_stats_source_correction"
    assert verdict["correct_stats"]==TARGETS[name]["proper_attrs"]
    assert verdict["writes"]==0
    assert row==before
    assert not monster_semantic_numeric_flags(verdict["correct_stats"])


@pytest.mark.parametrize(("field","invalid"),[
    ("id","wrong"),("user_id","wrong"),("name","wrong"),
    ("source_name","wrong"),("normalized_name","wrong"),
    ("reference_type","other"),("review_status","pending"),
    ("review_flags",["ocr_da_verificare"]),("canonical_id","another"),
    ("source_key","other.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),
    ("source_refs",[]),("attributes",{}),
    ("source_attributes",{"punti_ferita":"x"}),("review_corrections",{"x":True}),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_source_or_old_attributes_drift_rejected(original,field,invalid):
    name,row=original
    row[field]=invalid
    with pytest.raises(ValueError):
        audit_wrong_neighbor(name,row)


@pytest.mark.parametrize(("field","invalid"),[
    ("page",50),("logical_page",250),("filename","wrong.pdf"),
    ("source_role","secondary"),("authority_class","unlicensed"),
    ("source_status","inactive"),("logical_source_id","another"),
    ("ruleset","2024"),
])
def test_wrong_authority_or_adjacent_page_rejected(original,field,invalid):
    name,row=original
    row["source_refs"][0][field]=invalid
    with pytest.raises(ValueError):
        audit_wrong_neighbor(name,row)


def test_neighbor_identity_cannot_supply_stats(original):
    _,row=original
    with pytest.raises(ValueError):
        audit_wrong_neighbor("Serramorte",row)
    row["source_refs"].append(deepcopy(row["source_refs"][-1]))
    with pytest.raises(ValueError):
        audit_wrong_neighbor(row["name"],row)


def test_original_hp_average_and_global_semantics():
    for spec in TARGETS.values():
        hp,n,faces,bonus=spec["dice"]
        assert (n*(faces+1))//2+bonus==hp
        invalid=dict(spec["proper_attrs"])
        invalid["punti_ferita"]=f"{hp} ({n}d{faces} + {bonus+1})"
        assert monster_semantic_numeric_flags(invalid)
