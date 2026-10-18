"""Negative/provenance tests for source-audited Draghi d’Ottone."""
from copy import deepcopy
import pytest
from services import mm_brass_dragons_pages_115_117_source_review as mm

def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256,
        "physical_pages": mm.PAGE_COUNT,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"), [["Drago D’Ottone Antico",115,"297 (17d20 + 119)","20"],["Drago D’Ottone Adulto",116,"172 (15d12 + 75)","13"],["Drago D’Ottone Giovane",116,"110 (13d10 + 39)","6"],["Drago D’Ottone Cucciolo",117,"16 (3d8 + 3)","1"]])
def test_original_named_statblock(name,page,hp,gs):
    proof=mm.audit(name,catalog())
    assert proof["physical_page"] == page
    assert proof["attributes"]["punti_ferita"] == hp
    assert proof["attributes"]["grado_sfida"] == gs
    assert proof["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert proof["writes"] == 0

def test_unique_independent_named_age_classes():
    ids={mm.audit(name,catalog())["id"] for name in mm.MONSTERS}
    assert len(ids)==len(mm.MONSTERS)==4

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_duplicate_never_passes(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_id=True)
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),same_name_monsters=[{"name":name}])

def test_registered_pdf_mismatch_rejected():
    c=catalog()
    c["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="not_authorized"):
        mm.audit(next(iter(mm.MONSTERS)),c)

@pytest.mark.parametrize("change",["ac","hp","speed","gs","size","abilities"])
def test_plausible_mutated_data_rejected(monkeypatch,change):
    original=deepcopy(mm.MONSTERS)
    name=next(iter(original))
    if change=="abilities":
        original[name][change]["for"]=1
    elif change=="size":
        original[name][change]="Grande"
    else:
        original[name][change]+="0"
    monkeypatch.setattr(mm,"MONSTERS",original)
    with pytest.raises(ValueError,match="source_fields_changed"):
        mm.audit(name,catalog())
