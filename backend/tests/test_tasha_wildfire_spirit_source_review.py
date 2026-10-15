"""Strict split-role tests for Tasha Wildfire Spirit class feature and creature."""
import pytest
from services.tasha_wildfire_spirit_source_review import (
 ID, FEATURE_ID, NAME, SOURCE_FILE, CATALOG_FILE, SOURCE_ID, PAGE,
 SHA, CHECKSUM, ATTRS, OCR_ATTRS, SOURCE_TEXT, audit_wildfire_statblock,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags


def catalog():
    return {"logical_source_id": SOURCE_ID, "physical_filename": CATALOG_FILE,
            "physical_pages": 194, "source_status":"active",
            "authority_class":"licensed_translation", "source_role":"authority"}


def feature():
    return {
        "id": FEATURE_ID, "user_id":"user_fabf28726a20",
        "name":NAME, "source_name":NAME, "normalized_name":NAME.casefold(),
        "reference_type":"class_feature", "review_status":"pending",
        "review_flags":["ocr_da_verificare", "source_guided_repair"],
        "source_language":"it", "source_key":SOURCE_FILE,
        "source_text_checksum":CHECKSUM, "attributes":dict(ATTRS),
        "source_attributes":dict(OCR_ATTRS),
        "source_refs":[{"page":PAGE,"filename":SOURCE_FILE}],
        "canonical_id":None, "full_text":SOURCE_TEXT,"source_full_text":SOURCE_TEXT,
    }


def test_existing_feature_preserved_and_creature_eligible():
    row=feature()
    before=dict(row)
    result=audit_wildfire_statblock(None,None,row,catalog())
    assert row==before
    assert result["candidate_id"]==ID
    assert result["class_feature_left_unchanged"] is True
    assert result["writes"]==0
    assert len(SHA)==64 and not monster_semantic_numeric_flags(ATTRS)


@pytest.mark.parametrize(("key","bad"),[
    ("id","wrong"),("name","Wrong"),("reference_type","monster"),
    ("review_status","verified"),("review_flags",[]),
    ("attributes",{"classe_armatura":"13"}),("source_attributes",{}),
    ("source_refs",[]),("source_text_checksum","0"*64),
    ("full_text","changed"),("source_full_text","changed"),
])
def test_historical_feature_drift_blocks(key,bad):
    f=feature();f[key]=bad
    with pytest.raises(ValueError):
        audit_wildfire_statblock(None,None,f,catalog())


def test_wrong_catalog_or_existing_monster_blocks():
    with pytest.raises(ValueError):
        audit_wildfire_statblock({"id":ID},None,feature(),catalog())
    with pytest.raises(ValueError):
        audit_wildfire_statblock(None,{"id":"other"},feature(),catalog())
    c=catalog();c["physical_filename"]="other.pdf"
    with pytest.raises(ValueError):
        audit_wildfire_statblock(None,None,feature(),c)


def test_dynamic_formula_is_not_a_fixed_hit_point_total():
    assert monster_semantic_numeric_flags({"classe_armatura":"13",
        "punti_ferita":"5", "velocita":"9 m"})
