"""Read-only negative source audit tests for MM dinosaurs p79–80."""
from copy import deepcopy
import pytest
from services import mm_dinosaurs_pages_79_80_source_review as mm

def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,"physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256,"physical_pages": mm.PAGE_COUNT,
        "source_status": "active","source_role": "authority",
        "authority_class": "licensed_translation","text_mode": "vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"),[["Allosauro",79,"51 (6d10 + 18)","2"],["Anchilosauro",79,"68 (8d12 + 16)","3"],["Plesiosauro",80,"68 (8d10 + 24)","2"],["Pteranodonte",80,"13 (3d8)","1/4"],["Tirannosauro",80,"136 (13d12 + 52)","8"],["Triceratopo",80,"95 (10d12 + 30)","5"]])
def test_exact_source_p79_80(name,page,hp,gs):
    x=mm.audit(name,catalog())
    assert x["physical_page"]==page
    assert x["attributes"]["punti_ferita"]==hp
    assert x["attributes"]["grado_sfida"]==gs
    assert x["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert x["writes"]==0

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_id_and_name_duplicates_block(name):
    with pytest.raises(ValueError,match="already_existing"):
        mm.audit(name,catalog(),id_exists=True)
    with pytest.raises(ValueError,match="already_existing"):
        mm.audit(name,catalog(),monster_name_matches=[{"name":name}])

def test_both_dinosaurs_p79_are_separate():
    a=mm.audit("Allosauro",catalog())
    b=mm.audit("Anchilosauro",catalog())
    assert a["physical_page"]==b["physical_page"]==79 and a["id"]!=b["id"]

def test_four_distinct_p80():
    ids=[mm.audit(name,catalog())["id"] for name in ("Plesiosauro","Pteranodonte","Tirannosauro","Triceratopo")]
    assert len(ids)==len(set(ids))==4

@pytest.mark.parametrize("field",["physical_sha256","source_role","logical_source_id"])
def test_wrong_source_fails(field):
    bad=catalog()
    bad[field]="wrong"
    with pytest.raises(ValueError,match="registered_authority"):
        mm.audit("Allosauro",bad)

@pytest.mark.parametrize(("name","field","value"),[
    ("Allosauro","hp","52 (6d10 + 19)"),
    ("Anchilosauro","ac","14 (armatura naturale)"),
    ("Pteranodonte","gs","1/2"),
    ("Plesiosauro","speed","9 m"),
    ("Tirannosauro","size","Grande"),
    ("Triceratopo","hp","96 (10d12 + 31)"),
])
def test_changed_but_plausible_value_fails(name,field,value,monkeypatch):
    altered=deepcopy(mm.MONSTERS)
    altered[name][field]=value
    monkeypatch.setattr(mm,"MONSTERS",altered)
    with pytest.raises(ValueError):
        mm.audit(name,catalog())
