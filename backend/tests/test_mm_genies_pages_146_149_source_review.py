"""Tests: four genie source statblocks and fail-closed original fields."""
from copy import deepcopy
import pytest
from services import mm_genies_pages_146_149_source_review as mm

def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SOURCE_SHA256,
        "physical_pages": mm.PDF_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }

@pytest.mark.parametrize(("name", "page", "hp", "gs"), [
    ("Dao", 146, "187 (15d10 + 105)", "11"),
    ("Djinni", 147, "161 (14d10 + 84)", "11"),
    ("Efreeti", 148, "200 (16d10 + 112)", "11"),
    ("Marid", 149, "229 (17d10 + 136)", "11"),
])
def test_four_genies_independently_verified(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0

def test_unique_original_ids():
    values = [mm.audit(n, catalog())["id"] for n in mm.CREATURES]
    assert len(values) == len(set(values)) == 4

def test_p145_lore_does_not_become_creature():
    with pytest.raises(ValueError, match="no_independent"):
        mm.audit("Genio", catalog())

@pytest.mark.parametrize("name", list(mm.CREATURES))
def test_duplicate_never_promoted(name):
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), duplicate_id=True)
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), duplicate_names=[{"name": name}])

def test_physical_pdf_authority():
    c = catalog()
    c["physical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="registered_source"):
        mm.audit("Dao", c)

@pytest.mark.parametrize(("name", "field", "wrong"), [
    ("Dao", "hp", "188 (15d10 + 106)"),
    ("Djinni", "gs", "12"),
    ("Efreeti", "speed", "9 m"),
    ("Marid", "scores", [22, 12, 26, 18, 17, 17]),
    ("Dao", "actions", ["Multiattacco"]),
])
def test_modified_statblock_rejected(monkeypatch, name, field, wrong):
    changed = deepcopy(mm.CREATURES)
    changed[name][field] = wrong
    monkeypatch.setattr(mm, "CREATURES", changed)
    with pytest.raises(ValueError, match="sealed_source"):
        mm.audit(name, catalog())
