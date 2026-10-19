"""MM original p249–256: no duplicate Pseudodrago, seven independent statblocks."""
from copy import deepcopy
import pytest
from services import mm_orrore_quaggoth_pages_249_256_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256,
        "physical_pages": mm.PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize("name,page,hp,gs", [
    ("Orrore Uncinato", 249, "75 (10d10 + 20)", "3"),
    ("Orsogufo", 250, "59 (7d10 + 21)", "3"),
    ("Otyugh", 251, "114 (12d10 + 48)", "5"),
    ("Pegaso", 252, "59 (7d10 + 21)", "2"),
    ("Peryton", 253, "33 (6d8 + 6)", "2"),
    ("Pixie", 254, "1 (1d4 - 1)", "1/4"),
    ("Quaggoth", 256, "45 (6d8 + 18)", "2"),
])
def test_independently_source_checked_statblocks(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_cross_source_pseudodrago_dedup():
    assert len(mm.MONSTERS) == 7
    assert 255 not in [x["page"] for x in mm.MONSTERS.values()]
    assert mm.CROSS_SOURCE_OVERLAP["name"] == "Pseudodrago"
    assert mm.CROSS_SOURCE_OVERLAP["page"] == 255
    assert mm.CROSS_SOURCE_OVERLAP["decision"] == "reuse_existing_verified_monster_no_duplicate"
    assert mm.CROSS_SOURCE_OVERLAP["verified_against_full_record"] is False
    with pytest.raises(ValueError, match="existing_cross_source_same_core_stats"):
        mm.audit("Pseudodrago", catalog())


def test_original_authority_and_collision():
    broken = catalog()
    broken["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Orsogufo", broken)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Orsogufo", catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Orsogufo", catalog(), same_named_monster=True)


def test_sealed_mutation_and_defensive_copy():
    old = deepcopy(mm.MONSTERS["Peryton"])
    try:
        mm.MONSTERS["Peryton"]["hp"] = "40 (6d8 + 6)"
        with pytest.raises(ValueError, match="source_fields_changed"):
            mm.audit("Peryton", catalog())
    finally:
        mm.MONSTERS["Peryton"] = old
    v = mm.audit("Pixie", catalog())
    v["attributes"]["azioni_nomi_da_completare"].append("inventato")
    assert "inventato" not in mm.audit("Pixie", catalog())["attributes"]["azioni_nomi_da_completare"]
