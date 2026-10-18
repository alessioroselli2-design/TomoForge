"""Four original white dragons, fail-closed source and HP gates."""
from copy import deepcopy
import pytest
from services import mm_white_dragons_pages_87_89_source_review as mm

def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"),[["Drago Bianco Antico",87,"333 (18d20 + 144)","20"],["Drago Bianco Adulto",88,"200 (16d12 + 96)","13"],["Drago Bianco Giovane",88,"133 (14d10 + 56)","6"],["Drago Bianco Cucciolo",89,"32 (5d8 + 10)","2"]])
def test_original_four_age_brackets(name,page,hp,gs):
    row=mm.audit(name,catalog())
    assert row["physical_page"]==page
    assert row["attributes"]["punti_ferita"]==hp
    assert row["attributes"]["grado_sfida"]==gs
    assert row["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert row["writes"]==0

def test_two_boxes_on_p88():
    adult=mm.audit("Drago Bianco Adulto",catalog())
    young=mm.audit("Drago Bianco Giovane",catalog())
    assert adult["physical_page"]==young["physical_page"]==88
    assert adult["id"]!=young["id"]

def test_lore_is_not_monster():
    with pytest.raises(ValueError,match="no_named_original"):
        mm.audit("Drago Bianco",catalog())

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_preexisting_records_block(name):
    with pytest.raises(ValueError,match="already_exists"):
        mm.audit(name,catalog(),duplicate_id=True)
    with pytest.raises(ValueError,match="already_exists"):
        mm.audit(name,catalog(),duplicate_monsters=[{"name":name}])

@pytest.mark.parametrize("field",["physical_sha256","source_status","authority_class"])
def test_source_mismatch_fails(field):
    b=catalog()
    b[field]="bad"
    with pytest.raises(ValueError,match="unverified_registered"):
        mm.audit("Drago Bianco Antico",b)

@pytest.mark.parametrize(("name","field","wrong"),[
    ("Drago Bianco Antico","hp","334 (18d20 + 145)"),
    ("Drago Bianco Adulto","gs","14"),
    ("Drago Bianco Giovane","size","Enorme"),
    ("Drago Bianco Cucciolo","speed","12 m"),
])
def test_changed_original_stats_fail(monkeypatch,name,field,wrong):
    data=deepcopy(mm.MONSTERS)
    data[name][field]=wrong
    monkeypatch.setattr(mm,"MONSTERS",data)
    with pytest.raises(ValueError):
        mm.audit(name,catalog())
