"""Fail-closed source review: physical pp281-288 and cross-source alias."""
from copy import deepcopy
import pytest
from services import mm_succube_tarrasque_treant_pages_281_288_review as mm


def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }


@pytest.mark.parametrize("name,page,hp,gs", [
    ("Succube/Incubo", 282, "66 (12d8 + 12)", "4"),
    ("Tarrasque", 284, "676 (33d20 + 330)", "30"),
    ("Teschio Infuocato", 285, "40 (9d4 + 18)", "4"),
    ("Testuggine Dragona", 286, "341 (22d20 + 110)", "17"),
    ("Thri-Kreen", 287, "33 (6d8 + 6)", "1"),
    ("Treant", 288, "138 (12d12 + 60)", "9"),
])
def test_six_source_blocks(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert r["writes"]==0


def test_spritello_cross_source_alias_no_duplicate():
    assert len(mm.MONSTERS)==6
    assert mm.CROSS_SOURCE_OVERLAP["original_name"]=="Spritello"
    assert mm.CROSS_SOURCE_OVERLAP["existing_name"]=="Spiritello"
    assert mm.CROSS_SOURCE_OVERLAP["full_field_concordance_confirmed"] is False
    for alias in ("Spritello","Spiritello"):
        with pytest.raises(ValueError,match="cross_source_alias_pending_full_comparison"):
            mm.audit(alias,catalog())


def test_tarrasque_is_one_box_not_lore():
    assert 283 not in [d["page"] for d in mm.MONSTERS.values()]
    assert len({mm.audit(n,catalog())["id"] for n in mm.MONSTERS})==6
    assert mm.audit("Tarrasque",catalog())["attributes"]["grado_sfida"]=="30"
    assert len(mm.audit("Tarrasque",catalog())["attributes"]["azioni_leggendarie_nomi_da_completare"])==3


def test_authority_collision_mutation_defensive_copy():
    c=catalog()
    c["physical_sha256"]="fake"
    with pytest.raises(ValueError,match="original_source_mismatch"):
        mm.audit("Treant",c)
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit("Treant",catalog(),existing_id=True)
    old=deepcopy(mm.MONSTERS["Thri-Kreen"])
    try:
        mm.MONSTERS["Thri-Kreen"]["hp"]="33 (7d8 + 6)"
        with pytest.raises(ValueError,match="source_fields_changed"):
            mm.audit("Thri-Kreen",catalog())
    finally:
        mm.MONSTERS["Thri-Kreen"]=old
    r=mm.audit("Testuggine Dragona",catalog())
    r["attributes"]["caratteristiche"]["for"]="99"
    assert mm.audit("Testuggine Dragona",catalog())["attributes"]["caratteristiche"]["for"]=="25"
