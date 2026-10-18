"""Original source-locked red dragons p97-98, no DB writes."""
from copy import deepcopy
import pytest
from services import mm_red_dragons_pages_97_98_source_review as mm

def catalog():
    return {"logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
            "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
            "source_status":"active","source_role":"authority",
            "authority_class":"licensed_translation","text_mode":"vision_required"}

@pytest.mark.parametrize(("name","page","hp","gs"),[["Drago Rosso Antico",97,"546 (28d20 + 252)","24"],["Drago Rosso Adulto",98,"256 (19d12 + 133)","17"],["Drago Rosso Giovane",98,"178 (17d10 + 85)","10"],["Drago Rosso Cucciolo",98,"75 (10d8 + 30)","4"]])
def test_original_p97_98_stats(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["writes"]==0

def test_p98_three_boxes():
    items=[mm.audit(n,catalog()) for n in (
        "Drago Rosso Adulto","Drago Rosso Giovane","Drago Rosso Cucciolo")]
    assert all(x["physical_page"]==98 for x in items)
    assert len({x["id"] for x in items})==3

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_collision_fails_closed(name):
    with pytest.raises(ValueError,match="already_present"):
        mm.audit(name,catalog(),id_found=True)
    with pytest.raises(ValueError,match="already_present"):
        mm.audit(name,catalog(),other_monster_names=[{"name":name}])

def test_source_signature_cannot_change():
    wrong=catalog()
    wrong["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="source_authority"):
        mm.audit("Drago Rosso Antico",wrong)

@pytest.mark.parametrize(("name","field","changed"),[
    ("Drago Rosso Antico","hp","547 (28d20 + 253)"),
    ("Drago Rosso Adulto","gs","18"),
    ("Drago Rosso Giovane","size","Enorme"),
    ("Drago Rosso Cucciolo","speed","12 m"),
])
def test_changed_source_fails(name,field,changed,monkeypatch):
    data=deepcopy(mm.MONSTERS)
    data[name][field]=changed
    monkeypatch.setattr(mm,"MONSTERS",data)
    with pytest.raises(ValueError):
        mm.audit(name,catalog())
