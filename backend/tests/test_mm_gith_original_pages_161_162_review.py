"""Fail-closed source, collision and HP gates for quattro gith."""
from copy import deepcopy
import pytest
from services import mm_gith_original_pages_161_162_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256,
        "physical_pages": mm.PDF_PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }


@pytest.mark.parametrize(("name", "page", "hp", "gs"), [["Githyanki Combattente",161,"49 (9d8 + 9)","3"],["Githyanki Cavaliere",161,"91 (14d8 + 28)","8"],["Githzerai Monaco",162,"38 (7d8 + 7)","2"],["Githzerai Zerth",162,"84 (13d8 + 26)","6"]])
def test_original_page_and_core_stats(name, page, hp, gs):
    out = mm.audit(name, catalog())
    assert out["physical_page"] == page
    assert out["attributes"]["punti_ferita"] == hp
    assert out["attributes"]["grado_sfida"] == gs
    assert out["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert out["writes"] == 0


def test_independent_sealed_ids():
    results = [mm.audit(name, catalog()) for name in mm.CREATURES]
    assert len({r["id"] for r in results}) == len(mm.CREATURES)


@pytest.mark.parametrize("name", list(mm.CREATURES))
def test_duplicate_rejected(name):
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), existing_monsters=[{"name": name}])


def test_wrong_pdf_rejected():
    bad = catalog()
    bad["physical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="registered_authority"):
        mm.audit(next(iter(mm.CREATURES)), bad)


@pytest.mark.parametrize("name", list(mm.CREATURES))
def test_tampered_source_rejected(monkeypatch, name):
    changed = deepcopy(mm.CREATURES)
    changed[name]["hp"] = "100 (10d8 + 55)"
    monkeypatch.setattr(mm, "CREATURES", changed)
    with pytest.raises(ValueError, match="sealed_statblock"):
        mm.audit(name, catalog())


def test_return_is_defensive_copy():
    name = next(iter(mm.CREATURES))
    row = mm.audit(name, catalog())
    row["attributes"]["caratteristiche"]["for"] = "30"
    assert mm.CREATURES[name]["scores"][0] != 30

def test_gith_species_subtype_preserved():
    attrs = mm.audit("Githyanki Combattente", catalog())["attributes"]
    assert attrs["sottotipo_creatura"] == "gith"

