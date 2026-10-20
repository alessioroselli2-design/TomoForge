"""Source and negative regressions for original Italian MM pp257-260."""
from copy import deepcopy
import pytest

from services import mm_rakshasa_remorhaz_revenant_roc_pages_257_260_review as mm


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
    ("Rakshasa", 257, "110 (13d8 + 52)", "13"),
    ("Remorhaz Giovane", 258, "93 (11d10 + 33)", "5"),
    ("Remorhaz", 258, "195 (17d12 + 85)", "11"),
    ("Revenant", 259, "136 (16d8 + 64)", "5"),
    ("Roc", 260, "248 (16d20 + 80)", "11"),
])
def test_original_source_checked(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_remorhaz_young_and_adult_separate():
    assert len(mm.MONSTERS) == 5
    assert mm.audit("Remorhaz Giovane", catalog())["physical_page"] == 258
    assert mm.audit("Remorhaz", catalog())["physical_page"] == 258
    assert len({mm.audit(n, catalog())["id"] for n in mm.MONSTERS}) == 5


def test_fail_closed_invalid_source_and_duplicates():
    c = catalog()
    c["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Roc", c)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Roc", catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit("Roc", catalog(), same_named_monster=True)
    with pytest.raises(ValueError, match="not_an_original_statblock"):
        mm.audit("Remorhaz Falso", catalog())


def test_sealed_mutation_and_copy_protection():
    old = deepcopy(mm.MONSTERS["Revenant"])
    try:
        mm.MONSTERS["Revenant"]["gs"] = "20"
        with pytest.raises(ValueError, match="source_fields_changed"):
            mm.audit("Revenant", catalog())
    finally:
        mm.MONSTERS["Revenant"] = old
    x = mm.audit("Rakshasa", catalog())
    x["attributes"]["caratteristiche"]["cos"] = "99"
    assert mm.audit("Rakshasa", catalog())["attributes"]["caratteristiche"]["cos"] == "18"
