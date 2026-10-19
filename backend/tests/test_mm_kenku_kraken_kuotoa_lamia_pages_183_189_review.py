"""Fail-closed source and numeric tests for MM p183–189."""
from copy import deepcopy
import pytest
from services import mm_kenku_kraken_kuotoa_lamia_pages_183_189_review as mm

def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,
        "physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,
        "physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"),[["Kenku",183,"13 (3d8)","1/4"],["Kraken",185,"472 (27d20 + 189)","23"],["Kuo-Toa",187,"18 (4d8)","1/4"],["Kuo-Toa Gran Sacerdote",188,"97 (13d8 + 39)","6"],["Kuo-Toa Esecutore",188,"65 (10d8 + 20)","1"],["Lamia",189,"97 (13d10 + 26)","4"]])
def test_original_independent_boxes(name,page,hp,gs):
    row=mm.audit(name,catalog())
    assert row["physical_page"]==page
    assert row["attributes"]["punti_ferita"]==hp
    assert row["attributes"]["grado_sfida"]==gs
    assert row["writes"]==0

def test_two_kuo_toa_specialists_same_page_distinct_identity():
    a=mm.audit("Kuo-Toa Gran Sacerdote",catalog())
    b=mm.audit("Kuo-Toa Esecutore",catalog())
    assert a["id"]!=b["id"] and a["physical_page"]==b["physical_page"]==188

def test_kraken_legendary_details_remain_explicitly_pending():
    r=mm.audit("Kraken",catalog())["attributes"]
    assert "Azioni Leggendarie" in r["tratti_nomi_da_completare"]
    assert r["completezza_scheda"]=="statistiche_essenziali"

def test_lore_pages_do_not_create_monsters():
    with pytest.raises(ValueError,match="no_independent"):
        mm.audit("Kuo-Toa Divinità",catalog())

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_duplicate_monster_rejected(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_id=True)
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),same_name_monsters=[{"name":name}])

def test_pdf_source_mismatch_rejected():
    c=catalog();c["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="source_catalog"):
        mm.audit("Kenku",c)

@pytest.mark.parametrize(("name","field","value"),[
    ("Kenku","gs","1/2"),
    ("Kraken","hp","473 (27d20 + 190)"),
    ("Kuo-Toa","size","Grande"),
    ("Kuo-Toa Gran Sacerdote","scores",[16,14,17,13,16,14]),
    ("Kuo-Toa Esecutore","actions",["Morso"]),
    ("Lamia","hp","96 (13d10 + 25)"),
])
def test_tampered_core_fields_rejected(name,field,value,monkeypatch):
    changed=deepcopy(mm.MONSTERS);changed[name][field]=value
    monkeypatch.setattr(mm,"MONSTERS",changed)
    with pytest.raises(ValueError,match="original_source_fields"):
        mm.audit(name,catalog())
