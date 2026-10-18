"""Fail-closed source tests for four independent MM p133–136 monsters."""
from copy import deepcopy
import pytest
from services import mm_monsters_pages_133_136_source_review as mm

def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"),[["Fatale Dell'Acqua",133,"58 (9d10 + 9)","3"],["Fauce Gorgogliante",134,"67 (9d8 + 27)","2"],["Flumph",135,"7 (2d6)","1/8"],["Fomorian",136,"149 (13d12 + 65)","8"]])
def test_original_statblock(name,page,hp,gs):
    x=mm.audit(name,catalog())
    assert x["physical_page"]==page
    assert x["attributes"]["punti_ferita"]==hp
    assert x["attributes"]["grado_sfida"]==gs
    assert x["writes"]==0

def test_fomorian_bigby_lore_does_not_prevent_distinct_monster_record():
    x=mm.audit("Fomorian",catalog())
    assert x["attributes"]["tipo_creatura"]=="Gigante"

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_existing_monster_collision_fails(name):
    with pytest.raises(ValueError,match="duplicate_monster"):
        mm.audit(name,catalog(),duplicate_monster=True)

def test_wrong_pdf_is_not_authority():
    wrong=catalog()
    wrong["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="not_authorized"):
        mm.audit("Fomorian",wrong)

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_tampered_source_fails(monkeypatch,name):
    d=deepcopy(mm.MONSTERS)
    d[name]["gs"]="11"
    monkeypatch.setattr(mm,"MONSTERS",d)
    with pytest.raises(ValueError,match="sealed_source"):
        mm.audit(name,catalog())
