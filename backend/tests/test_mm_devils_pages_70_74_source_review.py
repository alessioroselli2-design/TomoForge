"""Source-locked Italian MM devil blocks, no DB mutations."""
from copy import deepcopy

import pytest

from services import mm_devils_pages_70_74_source_review as mm


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


@pytest.mark.parametrize(("name", "page", "hp", "gs"), [["Diavolo Barbuto",70,"52 (8d8 + 16)","3"],["Diavolo Cornuto",71,"178 (17d10 + 85)","11"],["Diavolo D'Ossa",72,"142 (15d10 + 60)","9"],["Diavolo Del Ghiaccio",73,"180 (19d10 + 76)","14"],["Diavolo Della Fossa",74,"300 (24d10 + 168)","20"]])
def test_separate_original_statblocks(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_preexisting_identity_always_rejected(name):
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit(name, catalog(), duplicate_monster_names=[{"name": name}])


def test_source_pdf_mismatch_fails():
    bad = catalog()
    bad["physical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="registered_source_changed"):
        mm.audit("Diavolo Barbuto", bad)


def test_original_statblock_change_detected(monkeypatch):
    copies = deepcopy(mm.MONSTERS)
    copies["Diavolo D'Ossa"]["hp"] = "143 (15d10 + 61)"
    monkeypatch.setattr(mm, "MONSTERS", copies)
    with pytest.raises(ValueError, match="sealed_original_stats_changed"):
        mm.audit("Diavolo D'Ossa", catalog())


def test_independent_original_page_ids():
    ids = {mm.audit(name, catalog())["id"] for name in mm.MONSTERS}
    assert len(ids) == len(mm.MONSTERS)
