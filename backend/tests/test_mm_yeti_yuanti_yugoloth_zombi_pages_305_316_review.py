"""Original Italian MM 305–316 provenance, statblocks and collision tests."""
from copy import deepcopy
import pytest
from services import mm_yeti_yuanti_yugoloth_zombi_pages_305_316_review as mm

def catalog():
    return {
        "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
        "physical_sha256":mm.SHA256,"physical_pages":mm.PAGES,
        "source_status":"active","source_role":"authority",
        "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize("name,page,hp,gs",[
    ("Yeti",305,"51 (6d10 + 18)","3"),
    ("Yeti Abominevole",306,"137 (11d12 + 66)","9"),
    ("Yuan-Ti Abominio",308,"127 (15d10 + 45)","7"),
    ("Yuan-Ti Nefasto",309,"66 (12d8 + 12)","3"),
    ("Yuan-Ti Sanguepuro",310,"40 (9d8)","1"),
    ("Arcanaloth",313,"104 (16d8 + 32)","12"),
    ("Mezzoloth",313,"75 (10d8 + 30)","5"),
    ("Nycaloth",314,"123 (13d10 + 52)","9"),
    ("Ultroloth",314,"153 (18d8 + 72)","13"),
    ("Zombi Ogre",316,"85 (9d10 + 36)","2"),
    ("Zombi Beholder",316,"93 (11d10 + 33)","5"),
])
def test_independent_original_statblock(name,page,hp,gs):
    result=mm.audit(name,catalog())
    assert result["physical_page"]==page
    assert result["attributes"]["punti_ferita"]==hp
    assert result["attributes"]["grado_sfida"]==gs
    assert result["attributes"]["completezza_scheda"]=="statistiche_essenziali"
    assert result["writes"]==0

def test_bestiary_statblocks_vs_lore_and_variants():
    assert len(mm.MONSTERS)==11
    assert len({mm.audit(n,catalog())["id"] for n in mm.MONSTERS})==11
    assert all(v["page"] not in (307,311,312,315) for v in mm.MONSTERS.values())
    assert sum(v["page"]==316 for v in mm.MONSTERS.values())==2
    assert "Tipo 3:" in mm.audit("Yuan-Ti Nefasto",catalog())["attributes"]["azioni_nomi_da_completare"][2]
    with pytest.raises(ValueError,match="cross_source_duplicate_phb_requires_full_check"):
        mm.audit("Zombi",catalog())
    assert mm.CROSS_SOURCE_OVERLAP["physical_page"]==316

def test_source_and_collision_fail_closed():
    bad=catalog();bad["physical_sha256"]="other"
    with pytest.raises(ValueError,match="original_source_mismatch"):
        mm.audit("Yeti",bad)
    with pytest.raises(ValueError,match="monster_collision"):
        mm.audit("Yeti",catalog(),same_named_monster=True)

def test_mutation_and_defensive_copy():
    old=deepcopy(mm.MONSTERS["Ultroloth"])
    try:
        mm.MONSTERS["Ultroloth"]["gs"]="99"
        with pytest.raises(ValueError,match="source_fields_changed"):
            mm.audit("Ultroloth",catalog())
    finally:
        mm.MONSTERS["Ultroloth"]=old
    a=mm.audit("Yeti",catalog());a["attributes"]["caratteristiche"]["for"]="0"
    assert mm.audit("Yeti",catalog())["attributes"]["caratteristiche"]["for"]=="18"


def test_cross_source_zombie_identity_is_preserved():
    overlap = mm.CROSS_SOURCE_OVERLAP
    assert overlap["name"] == "Zombi"
    assert overlap["physical_page"] == 316
    assert overlap["existing_page"] == 311
    assert overlap["existing_source"].startswith("Manuale_del_giocatore")
    assert overlap["common_core"] == {
        "classe_armatura": "8",
        "punti_ferita": "22 (3d8 + 9)",
        "velocita": "6 m",
    }
    assert "Zombi" not in mm.MONSTERS


def test_merged_yuanti_types_remain_one_monster():
    item = mm.audit("Yuan-Ti Nefasto", catalog())
    headings = item["attributes"]["azioni_nomi_da_completare"]
    assert len(headings) == 3
    assert all(heading.startswith(f"Tipo {n}:") for n, heading in enumerate(headings, 1))
    for name in ("Yuan-Ti Nefasto Tipo 1", "Yuan-Ti Nefasto Tipo 2"):
        with pytest.raises(ValueError, match="not_a_statblock"):
            mm.audit(name, catalog())
