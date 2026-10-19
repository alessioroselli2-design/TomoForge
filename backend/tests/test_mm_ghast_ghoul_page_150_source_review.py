"""Same physical page, two independent named undead source boxes."""
from copy import deepcopy
import pytest
from services import mm_ghast_ghoul_page_150_source_review as mm

def catalog():
    return {
       "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
       "physical_sha256":mm.SHA256,"physical_pages":mm.PDF_PAGES,
       "source_status":"active","source_role":"authority",
       "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","hp","gs"),[
    ("Ghast","36 (8d8)","2"),("Ghoul","22 (5d8)","1"),
])
def test_original_independent_box(name,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==150
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["writes"]==0

def test_two_different_ids_and_same_page():
    g1=mm.audit("Ghast",catalog())
    g2=mm.audit("Ghoul",catalog())
    assert g1["id"]!=g2["id"] and g1["physical_page"]==g2["physical_page"]==150

@pytest.mark.parametrize("name",["Ghast","Ghoul"])
def test_duplicate_monster_rejected(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),id_exists=True)
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),monster_duplicates=[{"name":name}])

def test_wrong_manual_hash_fails():
    bad=catalog()
    bad["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="invalid_authoritative"):
        mm.audit("Ghoul",bad)

@pytest.mark.parametrize("name",["Ghast","Ghoul"])
def test_modified_hp_fails(monkeypatch,name):
    copy=deepcopy(mm.MONSTERS)
    copy[name]["hp"]="100 (10d8 + 55)"
    monkeypatch.setattr(mm,"MONSTERS",copy)
    with pytest.raises(ValueError,match="sealed_original"):
        mm.audit(name,catalog())
