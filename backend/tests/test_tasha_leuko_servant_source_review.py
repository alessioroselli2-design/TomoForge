"""Source-specific non-write tests for Tasha Leuk-O construct monster."""
from copy import deepcopy
import pytest
import services.tasha_leuko_servant_source_review as source_review
from services.tasha_leuko_servant_source_review import (
    ID, NAME, ATTRS, SOURCE, CATALOG_FILE, SOURCE_ID, PHYSICAL_SHA256,
    audit_leuko_source,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

def catalog():
    return {
        "logical_source_id":SOURCE_ID,"physical_filename":CATALOG_FILE,
        "physical_pages":194,"physical_sha256":PHYSICAL_SHA256,
        "source_role":"authority","source_status":"active",
        "authority_class":"licensed_translation",
    }

def test_exact_source_and_no_duplicates_is_eligible_without_writes():
    c=catalog()
    before=deepcopy(c)
    result=audit_leuko_source(None,None,c)
    assert result["id"]==ID
    assert result["name"]==NAME
    assert result["status"]=="eligible_new_manual_visual_creature"
    assert result["writes"]==0 and result["automatic_ocr_not_claimed"] is True
    assert c==before
    assert not monster_semantic_numeric_flags(ATTRS)

@pytest.mark.parametrize(("id_row","name_row"),[
    ({"id":ID},None),(None,{"name":NAME}),
])
def test_duplicate_or_colliding_name_fails_closed(id_row,name_row):
    with pytest.raises(ValueError):
        audit_leuko_source(id_row,name_row,catalog())

@pytest.mark.parametrize(("field","bad"),[
    ("logical_source_id","other"),("physical_filename",SOURCE),
    ("physical_pages",150),("physical_sha256","0"*64),
    ("source_role","extraction_aid"),
    ("source_status","inactive"),("authority_class","unlicensed"),
])
def test_wrong_registered_catalog_fails_closed(field,bad):
    c=catalog()
    c[field]=bad
    with pytest.raises(ValueError):
        audit_leuko_source(None,None,c)

def test_source_missing_fails():
    with pytest.raises(ValueError):
        audit_leuko_source(None,None,None)

def test_corrupted_hp_expression_not_accepted_by_global_gate():
    changed={**ATTRS,"punti_ferita":"310 (27d12 + 134)"}
    assert monster_semantic_numeric_flags(changed)
    assert (27*13)//2+135==310


def test_changed_but_plausible_core_field_fails_closed(monkeypatch):
    changed={**ATTRS,"classe_armatura":"23 (armatura naturale)"}
    assert not monster_semantic_numeric_flags(changed)
    monkeypatch.setattr(source_review,"ATTRS",changed)
    with pytest.raises(ValueError,match="source_core_fields_disagree"):
        audit_leuko_source(None,None,catalog())


def test_unbound_heading_fails_closed(monkeypatch):
    monkeypatch.setattr(source_review,"EXCERPT",source_review.EXCERPT.replace(
        "Servitore Possente di Leuk-O. ","",1))
    with pytest.raises(ValueError,match="source_visual_excerpt_sha256_drift"):
        audit_leuko_source(None,None,catalog())


def test_returned_attributes_do_not_mutate_sealed_source():
    original=deepcopy(ATTRS)
    first=audit_leuko_source(None,None,catalog())
    first["attributes"]["injected"]="unverified value"
    assert ATTRS==original
    second=audit_leuko_source(None,None,catalog())
    assert second["attributes"]==original
    assert "injected" not in second["attributes"]
