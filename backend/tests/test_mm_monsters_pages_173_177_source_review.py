"""Fail-closed original source tests for Italian MM p173–177."""
from copy import deepcopy
import pytest

from services import mm_monsters_pages_173_177_source_review as mm


def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,
        "physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,
        "physical_pages":mm.PAGES,
        "source_status":"active",
        "source_role":"authority",
        "authority_class":"licensed_translation",
        "text_mode":"vision_required",
    }


@pytest.mark.parametrize(("name","page","hp","gs"),[["Grell",173,"55 (10d8 + 10)","3"],["Grick",174,"27 (6d8)","2"],["Grick Alfa",174,"75 (10d10 + 20)","7"],["Grifone",175,"59 (7d10 + 21)","2"],["Grimlock",176,"11 (2d8 + 2)","1/4"],["Guardiano Protettore",177,"142 (15d10 + 60)","7"]])
def test_original_box(name,page,hp,gs):
    row=mm.audit(name,catalog())
    assert row["physical_page"]==page
    assert row["attributes"]["punti_ferita"]==hp
    assert row["attributes"]["grado_sfida"]==gs
    assert row["writes"]==0


def test_grick_and_grick_alfa_same_page_different_record():
    normal=mm.audit("Grick",catalog())
    alfa=mm.audit("Grick Alfa",catalog())
    assert normal["physical_page"]==alfa["physical_page"]==174
    assert normal["id"]!=alfa["id"]


def test_grimlock_humanoid_not_monstrosity():
    attrs=mm.audit("Grimlock",catalog())["attributes"]
    assert attrs["tipo_creatura"]=="Umanoide"
    assert attrs["sottotipo_creatura"]=="grimlock"


@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_existing_monster_not_duplicated(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_id=True)
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_same_name_monsters=[{"name":name}])


def test_wrong_authority_cannot_pass():
    bad=catalog()
    bad["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="registered_source"):
        mm.audit("Grell",bad)


@pytest.mark.parametrize(("name","field","wrong"),[
    ("Grell","hp","56 (10d8 + 11)"),
    ("Grick","gs","3"),
    ("Grick Alfa","size","Media"),
    ("Grifone","speed","12 m"),
    ("Grimlock","scores",[15,12,12,9,8,6]),
    ("Guardiano Protettore","actions",["Pugno"]),
])
def test_tampered_source_is_rejected(name,field,wrong,monkeypatch):
    changed=deepcopy(mm.MONSTERS)
    changed[name][field]=wrong
    monkeypatch.setattr(mm,"MONSTERS",changed)
    with pytest.raises(ValueError,match="sealed_original"):
        mm.audit(name,catalog())


def test_caller_result_cannot_mutate_original():
    original=deepcopy(mm.MONSTERS["Grifone"])
    row=mm.audit("Grifone",catalog())
    row["attributes"]["caratteristiche"]["for"]="30"
    row["attributes"]["azioni_nomi_da_completare"].append("Magia")
    assert original==mm.MONSTERS["Grifone"]
