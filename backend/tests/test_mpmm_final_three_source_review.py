"""Fail-closed licensed MPMM statblock source checks for final candidate trio."""
from copy import deepcopy
import hashlib

import pytest

import services.mpmm_final_three_source_review as m
from services.mpmm_final_three_source_review import (
    OWNER, SOURCE, TARGETS, BARD_ID, BARD_CHECKSUM,
    BARD_ATTRIBUTES, PHYSICAL_SHA256, authority, audit_bard, audit_new_creature,
)

BARD_TEST_RAW = "Synthetic Bard original narrative for independent tests. " * 5


def catalog():
    return {
        "logical_source_id":"mpmm_2022_it","physical_filename":SOURCE,
        "physical_pages":100,"physical_sha256":PHYSICAL_SHA256,
        "source_status":"active",
        "authority_class":"licensed_translation","source_role":"authority",
    }


def bard():
    return {
        "id":BARD_ID,"user_id":OWNER,"name":"Bardo","source_name":"Bardo",
        "normalized_name":"bardo","reference_type":"class",
        "review_status":"verified","review_flags":[],
        "canonical_id":None,"source_key":SOURCE,"source_language":"it",
        "source_text_checksum":BARD_CHECKSUM,"source_refs":[authority(66)],
        "attributes":{},"source_attributes":{},"review_corrections":{},
        "full_text":BARD_TEST_RAW,"source_full_text":BARD_TEST_RAW,
    }


@pytest.mark.parametrize("name",list(TARGETS))
def test_new_original_monster_with_no_duplicates_passes(name):
    verdict=audit_new_creature(name,None,None,catalog())
    assert verdict["status"]=="eligible_new_source_named_monster"
    assert verdict["attributes"]==TARGETS[name]["attrs"]
    assert verdict["writes"]==0
    assert verdict["manual_visual_transcription"] is True


@pytest.mark.parametrize("name",list(TARGETS))
def test_duplicate_by_id_or_normalized_name_blocks(name):
    with pytest.raises(ValueError):
        audit_new_creature(name,{"id":TARGETS[name]["id"]},None,catalog())
    with pytest.raises(ValueError):
        audit_new_creature(name,None,{"name":name},catalog())


@pytest.mark.parametrize(("field","bad"),[
    ("physical_filename","wrong.pdf"),("logical_source_id","other"),
    ("physical_pages",50),("physical_sha256","0"*64),
    ("source_status","inactive"),
    ("authority_class","unlicensed"),("source_role","secondary"),
])
def test_wrong_catalog_blocks_new_creature(field,bad):
    c=catalog()
    c[field]=bad
    with pytest.raises(ValueError):
        audit_new_creature("Alkilith",None,None,c)


def test_missing_catalog_rejected():
    with pytest.raises(ValueError):
        audit_new_creature("Alkilith",None,None,None)


def test_source_excerpt_hash_drift_rejected(monkeypatch):
    t=deepcopy(TARGETS)
    t["Alkilith"]["source_excerpt"]+=" FAKE"
    monkeypatch.setattr(m,"TARGETS",t)
    with pytest.raises(ValueError):
        audit_new_creature("Alkilith",None,None,catalog())


def test_unregistered_creature_name_rejected():
    with pytest.raises(ValueError):
        audit_new_creature("Derro",None,None,catalog())


def test_exact_bard_class_record_source_can_be_reclassified(monkeypatch):
    monkeypatch.setattr(m,"BARD_SHA",hashlib.sha256(BARD_TEST_RAW.encode()).hexdigest())
    original=bard()
    before=deepcopy(original)
    verdict=audit_bard(original,None)
    assert verdict["status"]=="eligible_bard_NPC_reclassification"
    assert verdict["attributes"]==BARD_ATTRIBUTES
    assert verdict["writes"]==0
    assert before==original


@pytest.mark.parametrize(("key","bad"),[
    ("id","other"),("name","other"),("source_name","other"),
    ("normalized_name","wrong"),("reference_type","monster"),
    ("review_status","pending"),("review_flags",["ocr_da_verificare"]),
    ("canonical_id","other"),("source_key","wrong.pdf"),
    ("source_text_checksum","0"*64),("source_refs",[]),
    ("attributes",{"punti_ferita":"44"}),("source_attributes",{"punti_ferita":"44"}),
    ("review_corrections",{"changed":True}),
    ("full_text","other"),("source_full_text","other"),
])
def test_original_Bard_record_drift_blocks(key,bad,monkeypatch):
    monkeypatch.setattr(m,"BARD_SHA",hashlib.sha256(BARD_TEST_RAW.encode()).hexdigest())
    original=bard()
    original[key]=bad
    with pytest.raises(ValueError):
        audit_bard(original,None)


def test_source_Bard_page_is_exact(monkeypatch):
    monkeypatch.setattr(m,"BARD_SHA",hashlib.sha256(BARD_TEST_RAW.encode()).hexdigest())
    original=bard()
    original["source_refs"][0]["page"]=67
    with pytest.raises(ValueError):
        audit_bard(original,None)


def test_all_three_hit_dice_are_mathematically_consistent():
    from services.ocr_semantic_gates import monster_semantic_numeric_flags
    for spec in TARGETS.values():
        hp,n,faces,bonus=spec["dice"]
        assert n*(faces+1)//2+bonus==hp
        assert not monster_semantic_numeric_flags(spec["attrs"])
    assert not monster_semantic_numeric_flags(BARD_ATTRIBUTES)


@pytest.mark.parametrize("name",list(TARGETS))
def test_valid_but_different_armor_class_fails_source_parity(monkeypatch,name):
    specs=deepcopy(TARGETS)
    specs[name]["attrs"]["classe_armatura"]="18 (armatura naturale)"
    monkeypatch.setattr(m,"TARGETS",specs)
    with pytest.raises(ValueError,match="source_core_fields_disagree"):
        audit_new_creature(name,None,None,catalog())


def test_excerpt_must_include_its_own_heading(monkeypatch):
    specs=deepcopy(TARGETS)
    specs["Alkilith"]["source_excerpt"]=specs["Alkilith"]["source_excerpt"].replace("Alkilith. ","",1)
    monkeypatch.setattr(m,"TARGETS",specs)
    with pytest.raises(ValueError,match="manual_original_visual_excerpt_modified"):
        audit_new_creature("Alkilith",None,None,catalog())


def test_bardo_existing_monster_collision_rejected():
    with pytest.raises(ValueError,match="same_source_bard_monster_collision"):
        audit_bard(bard(),{"name":"Bardo","reference_type":"monster"})
