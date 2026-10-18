"""Fail-closed source tests for Italian Monster Manual p75–78."""
from copy import deepcopy
import pytest
from services import mm_devils_pages_75_78_source_review as mm

def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256,
        "physical_pages": mm.PAGE_COUNT,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }

@pytest.mark.parametrize(("name","page","pf","gs"),[["Diavolo Delle Catene",75,"85 (10d8 + 40)","8"],["Diavolo Spinato",76,"22 (5d6 + 5)","2"],["Diavolo Uncinato",76,"110 (13d8 + 52)","5"],["Erinni",77,"153 (18d8 + 72)","12"],["Lemure",78,"13 (3d8)","0"]])
def test_source_eligible(name,page,pf,gs):
    result=mm.audit(name,catalog())
    assert result["physical_page"]==page
    assert result["attributes"]["punti_ferita"]==pf
    assert result["attributes"]["grado_sfida"]==gs
    assert result["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert result["writes"]==0

def test_two_separate_devils_on_p76():
    a=mm.audit("Diavolo Spinato",catalog())
    b=mm.audit("Diavolo Uncinato",catalog())
    assert a["physical_page"]==b["physical_page"]==76
    assert a["id"]!=b["id"]

def test_original_imp_already_in_phb():
    assert mm.IMPORTED_IMP_ID=="ref_6e1a9996179d5a93a027a31bc30b5d2f"
    with pytest.raises(ValueError,match="already_verified_phb"):
        mm.audit("Imp",catalog())

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_collision_prevents_write(name):
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit(name,catalog(),found_by_id=True)
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit(name,catalog(),duplicate_monsters=[{"name":name}])

@pytest.mark.parametrize("field",["logical_source_id","physical_sha256","source_role","physical_pages"])
def test_wrong_authority_fails(field):
    bad=catalog()
    bad[field]="wrong"
    with pytest.raises(ValueError,match="registered_source"):
        mm.audit("Erinni",bad)

@pytest.mark.parametrize(("name","field","wrong"),[
    ("Lemure","hp","14 (3d8)"),
    ("Diavolo Spinato","gs","3"),
    ("Diavolo Uncinato","size","Grande"),
    ("Erinni","ac","19 (armatura completa)"),
    ("Diavolo Delle Catene","speed","12 m"),
])
def test_original_numbers_are_sealed(name,field,wrong,monkeypatch):
    changed=deepcopy(mm.MONSTERS)
    changed[name][field]=wrong
    monkeypatch.setattr(mm,"MONSTERS",changed)
    with pytest.raises(ValueError,match="statblock_source_fields_modified"):
        mm.audit(name,catalog())
