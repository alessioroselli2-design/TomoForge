"""Original-source and negative tests for Empireo, Ettercap, Ettin, Fantasma."""
from copy import deepcopy
import pytest
from services import mm_pages_129_132_source_review as mm

def catalog():
    return {
      "logical_source_id":mm.SOURCE_ID,
      "physical_filename":mm.FILENAME,
      "physical_sha256":mm.SHA256,
      "physical_pages":mm.PAGE_COUNT,
      "source_status":"active","source_role":"authority",
      "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"),[["Empireo",129,"313 (19d12 + 190)","23"],["Ettercap",130,"44 (8d8 + 8)","2"],["Ettin",131,"85 (10d10 + 30)","4"],["Fantasma",132,"45 (10d8)","4"]])
def test_statblocks(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["writes"]==0

def test_empireo_preserves_chance_for_each_alignment():
    result=mm.audit("Empireo",catalog())
    chance=result["attributes"]["allineamento_varianti_percentuali"]
    assert chance=={"caotico buono":75,"neutrale malvagio":25}
    assert sum(chance.values())==100

def test_fantasma_any_alignment_is_not_forced():
    assert mm.audit("Fantasma",catalog())["attributes"]["allineamento"]=="qualsiasi allineamento"

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_no_duplicate(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_monster=True)

def test_wrong_source_fails():
    bad=catalog()
    bad["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="unverified_original"):
        mm.audit("Empireo",bad)

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_changed_hp_fails(monkeypatch,name):
    bad=deepcopy(mm.MONSTERS)
    bad[name]["hp"]="100 (10d8 + 55)"
    monkeypatch.setattr(mm,"MONSTERS",bad)
    with pytest.raises(ValueError,match="sealed_fields"):
        mm.audit(name,catalog())
