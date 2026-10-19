"""Original Italian MM p164-167 six separate gnoll/goblin/gnome blocks."""
from copy import deepcopy
import pytest
from services import mm_gnoll_goblin_gnome_pages_164_167_review as mm

def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"),[["Gnoll",164,"22 (5d8)","1/2"],["Gnoll Signore Del Branco",164,"49 (9d8 + 9)","2"],["Gnoll Zanna Di Yeenoghu",164,"65 (10d8 + 20)","4"],["Gnomo Delle Profondità (Svirfneblin)",165,"16 (3d6 + 6)","1/2"],["Goblin",167,"7 (2d6)","1/4"],["Goblin Capo",167,"21 (6d6)","1"]])
def test_original_statblocks(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["writes"]==0

def test_gnoll_fang_is_fiend_not_humanoid():
    a=mm.audit("Gnoll Zanna Di Yeenoghu",catalog())
    b=mm.audit("Gnoll",catalog())
    assert a["attributes"]["tipo_creatura"]=="Immondo"
    assert b["attributes"]["tipo_creatura"]=="Umanoide"
    assert a["id"]!=b["id"]

def test_three_p164_and_two_p167_independent_boxes():
    grouped={}
    for n in mm.MONSTERS:
        r=mm.audit(n,catalog())
        grouped.setdefault(r["physical_page"],[]).append(r["id"])
    assert len(set(grouped[164]))==3
    assert len(set(grouped[167]))==2

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_duplicates_blocked(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),duplicate_id=True)
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),duplicate_monsters=[{"name":name}])

def test_wrong_pdf_source_rejected():
    bad=catalog()
    bad["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="unregistered_original"):
        mm.audit("Goblin",bad)

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_source_core_tampering_rejected(monkeypatch,name):
    changed=deepcopy(mm.MONSTERS)
    changed[name]["gs"]="10"
    monkeypatch.setattr(mm,"MONSTERS",changed)
    with pytest.raises(ValueError,match="sealed_source"):
        mm.audit(name,catalog())
