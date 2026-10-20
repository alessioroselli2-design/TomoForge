"""Protection for Quasit deduplication and two original demon statblocks."""
from copy import deepcopy

import pytest

from services import mm_demons_pages_63_65_source_review as mm


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


@pytest.mark.parametrize(("name", "page", "hp"), [
    ("Vrock", 64, "104 (11d10 + 44)"),
    ("Yochlol", 65, "136 (16d8 + 64)"),
])
def test_two_source_confirmed_statblocks(name, page, hp):
    r = mm.audit(name, catalog())
    assert r["page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["writes"] == 0


def test_quasit_already_verified_in_phb_not_new():
    assert mm.PHB_QUASIT_ID == "ref_867c68436df55ff48716ebe704da4044"
    with pytest.raises(ValueError, match="already_verified_phb"):
        mm.audit("Quasit", catalog())


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_duplicate_monster_rejected(name):
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), id_found=True)
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), names_found=[{"name": name}])


def test_wrong_pdf_does_not_pass():
    bad = catalog()
    bad["physical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="registered_source"):
        mm.audit("Vrock", bad)


def test_modified_stats_cannot_pass(monkeypatch):
    changed = deepcopy(mm.MONSTERS)
    changed["Yochlol"]["gs"] = "11"
    monkeypatch.setattr(mm, "MONSTERS", changed)
    with pytest.raises(ValueError, match="source_statblock_drift"):
        mm.audit("Yochlol", catalog())
