"""Five independent original MM p169-172 boxed monsters, fail-closed tests."""
from copy import deepcopy
import pytest
from services import mm_golems_gorgone_pages_169_172_review as mm

def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID, "physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"),[["Golem Di Argilla",169,"133 (14d10 + 56)","9"],["Golem Di Carne",170,"93 (11d8 + 44)","5"],["Golem Di Ferro",171,"210 (20d10 + 100)","16"],["Golem Di Pietra",171,"178 (17d10 + 85)","10"],["Gorgone",172,"114 (12d10 + 48)","5"]])
def test_original_golems_and_gorgone(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["writes"]==0

def test_golems_have_distinct_ids_even_when_same_page():
    a=mm.audit("Golem Di Ferro",catalog())
    b=mm.audit("Golem Di Pietra",catalog())
    assert a["physical_page"]==b["physical_page"]==171
    assert a["id"]!=b["id"]

def test_constructs_not_monstrosity():
    assert mm.audit("Golem Di Argilla",catalog())["attributes"]["tipo_creatura"]=="Costrutto"
    assert mm.audit("Gorgone",catalog())["attributes"]["tipo_creatura"]=="Mostruosità"

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_no_duplicate_monster_promoted(name):
    with pytest.raises(ValueError,match="already_imported"):
        mm.audit(name,catalog(),existing_monster=True)

def test_source_mismatch_fails():
    bad=catalog()
    bad["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="source_authority"):
        mm.audit("Golem Di Ferro",bad)

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_mutated_statblock_rejected(name,monkeypatch):
    changed=deepcopy(mm.MONSTERS)
    changed[name]["hp"]="99 (10d8 + 54)"
    monkeypatch.setattr(mm,"MONSTERS",changed)
    with pytest.raises(ValueError,match="sealed_source"):
        mm.audit(name,catalog())
