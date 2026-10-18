"""Fail-closed source tests for the four Italian MM blue dragons."""
from copy import deepcopy
import pytest
from services import mm_blue_dragons_pages_91_92_source_review as mm

def catalog():
    return {"logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
            "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
            "source_status":"active","source_role":"authority",
            "authority_class":"licensed_translation","text_mode":"vision_required"}

@pytest.mark.parametrize(("name","page","hp","gs"),[["Drago Blu Antico",91,"481 (26d20 + 208)","23"],["Drago Blu Adulto",92,"225 (18d12 + 108)","16"],["Drago Blu Giovane",92,"152 (16d10 + 64)","9"],["Drago Blu Cucciolo",92,"52 (8d8 + 16)","3"]])
def test_blue_dragon_original(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["writes"]==0

def test_three_distinct_boxes_on_page_92():
    names=("Drago Blu Adulto","Drago Blu Giovane","Drago Blu Cucciolo")
    data=[mm.audit(name,catalog()) for name in names]
    assert all(r["physical_page"]==92 for r in data)
    assert len({r["id"] for r in data})==3

def test_lore_only_page_93_excluded():
    with pytest.raises(ValueError,match="unknown_printed"):
        mm.audit("Drago Blu",catalog())

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_existing_monster_never_overwritten(name):
    with pytest.raises(ValueError,match="existing_monster"):
        mm.audit(name,catalog(),id_exists=True)
    with pytest.raises(ValueError,match="existing_monster"):
        mm.audit(name,catalog(),duplicate_monsters=[{"name":name}])

def test_unregistered_source_rejected():
    fake=catalog()
    fake["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="original_registered"):
        mm.audit("Drago Blu Antico",fake)

@pytest.mark.parametrize(("name","field","wrong"),[
    ("Drago Blu Antico","hp","482 (26d20 + 209)"),
    ("Drago Blu Adulto","size","Grande"),
    ("Drago Blu Giovane","gs","10"),
    ("Drago Blu Cucciolo","speed","12 m"),
])
def test_changed_original_fields_blocked(monkeypatch,name,field,wrong):
    temp=deepcopy(mm.MONSTERS)
    temp[name][field]=wrong
    monkeypatch.setattr(mm,"MONSTERS",temp)
    with pytest.raises(ValueError):
        mm.audit(name,catalog())
