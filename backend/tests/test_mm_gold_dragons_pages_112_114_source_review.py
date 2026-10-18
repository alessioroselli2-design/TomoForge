"""Negative/provenance tests for source-audited Draghi d'Oro."""
from copy import deepcopy
import pytest
from services import mm_gold_dragons_pages_112_114_source_review as mm

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

@pytest.mark.parametrize(("name","page","hp","gs"), [["Drago D’Oro Antico",112,"546 (28d20 + 252)","24"],["Drago D’Oro Adulto",113,"256 (19d12 + 133)","17"],["Drago D’Oro Giovane",114,"178 (17d10 + 85)","10"],["Drago D’Oro Cucciolo",114,"60 (8d8 + 24)","3"]])
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
