"""Fail-closed original source tests: four black dragons p94-95."""
from copy import deepcopy
import pytest
from services import mm_black_dragons_pages_94_95_source_review as mm

def catalog():
    return {"logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
            "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
            "source_status":"active","source_role":"authority",
            "authority_class":"licensed_translation","text_mode":"vision_required"}

@pytest.mark.parametrize(("name","page","hp","gs"),[["Drago Nero Antico",94,"367 (21d20 + 147)","21"],["Drago Nero Adulto",95,"195 (17d12 + 85)","14"],["Drago Nero Giovane",95,"127 (15d10 + 45)","7"],["Drago Nero Cucciolo",95,"33 (6d8 + 6)","2"]])
def test_visual_source_block(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["writes"]==0

def test_three_statblocks_on_p95():
    arr=[mm.audit(name,catalog()) for name in (
        "Drago Nero Adulto","Drago Nero Giovane","Drago Nero Cucciolo")]
    assert all(x["physical_page"]==95 for x in arr)
    assert len({x["id"] for x in arr})==3

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_no_duplicate_created(name):
    with pytest.raises(ValueError,match="existing_monster"):
        mm.audit(name,catalog(),existing_id=True)
    with pytest.raises(ValueError,match="existing_monster"):
        mm.audit(name,catalog(),duplicate_monsters=[{"name":name}])

def test_wrong_manual_is_not_authoritative():
    d=catalog()
    d["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="original_source"):
        mm.audit("Drago Nero Antico",d)

@pytest.mark.parametrize(("name","field","wrong"),[
    ("Drago Nero Antico","hp","368 (21d20 + 148)"),
    ("Drago Nero Adulto","gs","15"),
    ("Drago Nero Giovane","size","Enorme"),
    ("Drago Nero Cucciolo","speed","12 m"),
])
def test_source_changed_cannot_pass(monkeypatch,name,field,wrong):
    obj=deepcopy(mm.MONSTERS)
    obj[name][field]=wrong
    monkeypatch.setattr(mm,"MONSTERS",obj)
    with pytest.raises(ValueError):
        mm.audit(name,catalog())
