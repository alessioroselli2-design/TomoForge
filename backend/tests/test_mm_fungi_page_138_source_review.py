"""Fail-closed tests for p138 fungus statblocks and signed HP."""
from copy import deepcopy
import pytest
from services import mm_fungi_page_138_source_review as mm

def catalog():
    return {
       "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
       "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
       "source_status":"active","source_role":"authority",
       "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","hp","gs"),[
    ("Boleto Stridente","13 (3d8)","0"),
    ("Fungo Viola","18 (4d8)","1/4"),
    ("Spora Gassosa","1 (1d10 - 4)","1/2"),
])
def test_source_core(name,hp,gs):
    row=mm.audit(name,catalog())
    assert row["physical_page"]==138
    assert row["attributes"]["punti_ferita"]==hp
    assert row["attributes"]["grado_sfida"]==gs
    assert row["writes"]==0

def test_gas_spore_negative_hp_is_real_source_and_mathematically_correct():
    row=mm.audit("Spora Gassosa",catalog())
    assert row["attributes"]["punti_ferita"]=="1 (1d10 - 4)"
    assert 1*(10+1)//2-4==1

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_duplicate_is_rejected(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_monster=True)

def test_pdf_hash_mismatch():
    bad=catalog()
    bad["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="unverified_pdf"):
        mm.audit("Spora Gassosa",bad)

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_changed_value_rejected(monkeypatch,name):
    v=deepcopy(mm.MONSTERS)
    v[name]["gs"]="5"
    monkeypatch.setattr(mm,"MONSTERS",v)
    with pytest.raises(ValueError,match="original_statblock"):
        mm.audit(name,catalog())
