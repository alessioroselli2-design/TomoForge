"""Named statblocks and conditional GS constraints, Italian MM p118–121."""
from copy import deepcopy
import pytest
from services import mm_forest_underdark_pages_118_121_review as mm

def catalog():
    return {
       "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
       "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
       "source_status":"active","source_role":"authority",
       "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"), [
  ("Driade",119,"22 (5d8)","1"),
  ("Drider",120,"123 (13d10 + 52)","6"),
  ("Duergar",121,"26 (4d8 + 8)","1"),
])
def test_original_core(name,page,hp,gs):
    result=mm.audit(name,catalog())
    assert result["physical_page"]==page
    assert result["attributes"]["punti_ferita"]==hp
    assert result["attributes"]["grado_sfida"]==gs
    assert result["writes"]==0

def test_faerie_dragon_never_falsely_uses_single_gs():
    r=mm.audit("Drago Fatato",catalog())
    assert r["status"].startswith("blocked_multi_challenge")
    assert r["challenge_by_colour"]["rosso"]=="1"
    assert r["challenge_by_colour"]["viola"]=="2"
    assert r["writes"]==0

def test_duergar_species_lore_does_not_count_as_monster_collision():
    r=mm.audit("Duergar",catalog(),existing_monster=False)
    assert r["name"]=="Duergar"

@pytest.mark.parametrize("name",["Driade","Drider","Duergar","Drago Fatato"])
def test_true_monster_duplicate_never_promoted(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_monster=True)

def test_original_authority_sha_is_required():
    c=catalog()
    c["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="not_authorized"):
        mm.audit("Drider",c)

@pytest.mark.parametrize("name",["Driade","Drider","Duergar"])
def test_mutation_is_rejected(name,monkeypatch):
    tampered=deepcopy(mm.MONSTERS)
    tampered[name]["hp"]="100 (10d8 + 55)"
    monkeypatch.setattr(mm,"MONSTERS",tampered)
    with pytest.raises(ValueError,match="source_fields_changed"):
        mm.audit(name,catalog())
