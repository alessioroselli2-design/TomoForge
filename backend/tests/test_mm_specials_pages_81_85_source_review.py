"""Fail-closed tests for MM special boxed creatures p81-85."""
from copy import deepcopy
import pytest
from services import mm_specials_pages_81_85_source_review as mm

def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGE_COUNT,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"),[["Divoracervelli",81,"21 (6d4 + 6)","2"],["Doppelganger",82,"52 (8d8 + 16)","3"],["Dracolich Blu Adulto",84,"225 (18d12 + 108)","17"],["Drago D’Ombra Rosso Giovane",85,"178 (17d10 + 85)","13"]])
def test_checked_independent_boxes(name,page,hp,gs):
    got=mm.audit(name,catalog())
    assert got["physical_page"]==page
    assert got["attributes"]["punti_ferita"]==hp
    assert got["attributes"]["grado_sfida"]==gs
    assert got["writes"]==0

def test_archetype_prose_not_a_monster():
    with pytest.raises(ValueError,match="not_a_sealed"):
        mm.audit("Dracolich",catalog())

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_duplicate_is_fail_closed(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_id=True)
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_monster_names=[{"name":name}])

def test_ability_category_doppelganger_does_not_replace_the_monster():
    r=mm.audit("Doppelganger",catalog(),existing_monster_names=[])
    assert r["name"]=="Doppelganger"

@pytest.mark.parametrize("field",["physical_sha256","physical_filename","source_role"])
def test_wrong_pdf_is_rejected(field):
    bad=catalog()
    bad[field]="incorrect"
    with pytest.raises(ValueError,match="source_authority"):
        mm.audit("Divoracervelli",bad)

@pytest.mark.parametrize(("name","field","wrong"),[
    ("Divoracervelli","hp","22 (6d4 + 7)"),
    ("Doppelganger","size","Grande"),
    ("Dracolich Blu Adulto","gs","18"),
    ("Drago D’Ombra Rosso Giovane","speed","15 m"),
])
def test_modified_source_does_not_pass(name,field,wrong,monkeypatch):
    d=deepcopy(mm.MONSTERS)
    d[name][field]=wrong
    monkeypatch.setattr(mm,"MONSTERS",d)
    with pytest.raises(ValueError):
        mm.audit(name,catalog())
