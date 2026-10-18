"""Fail-closed tests for the first three Italian Monster Manual statblocks."""

from copy import deepcopy

import pytest

from services import mm_first_three_source_review as review


def _catalog():
    return {
        "logical_source_id": review.SOURCE_ID,
        "physical_filename": review.SOURCE_FILENAME,
        "physical_sha256": review.SOURCE_SHA256,
        "physical_pages": review.SOURCE_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize("name,page,ac,pf,gs", [
    ("Deva", 16, "17 (armatura naturale)", "136 (16d8 + 64)", "10"),
    ("Planetar", 17, "19 (armatura naturale)", "200 (16d10 + 112)", "16"),
    ("Solar", 18, "21 (armatura naturale)", "243 (18d10 + 144)", "21"),
])
def test_original_page_and_exact_statblock(name, page, ac, pf, gs):
    result = review.audit_mm_angel(name, None, [], _catalog())
    assert result["source_page"] == page
    assert result["attributes"]["classe_armatura"] == ac
    assert result["attributes"]["punti_ferita"] == pf
    assert result["attributes"]["grado_sfida"] == gs
    assert result["source_excerpt_sha256"] == review.ANGELS[name]["excerpt_sha256"]
    assert result["automatic_ocr_not_accepted_as_truth"] is True
    assert result["writes"] == 0


@pytest.mark.parametrize("name", ["Deva", "Planetar", "Solar"])
def test_never_overwrite_prior_record_or_mutate_source_constants(name):
    before = deepcopy(review.ANGELS[name])
    with pytest.raises(ValueError, match="already_present"):
        review.audit_mm_angel(name, {"id": before["id"]}, [], _catalog())
    with pytest.raises(ValueError, match="already_present"):
        review.audit_mm_angel(name, None, [{"name": name}], _catalog())
    result = review.audit_mm_angel(name, None, [], _catalog())
    result["attributes"]["caratteristiche"]["for"] = "1"
    assert review.ANGELS[name] == before


@pytest.mark.parametrize("field,bad", [
    ("logical_source_id", "phb_2014_it"),
    ("physical_filename", "Manuale del Giocatore.pdf"),
    ("physical_sha256", "0" * 64),
    ("physical_pages", 321),
    ("source_role", "extraction_aid"),
    ("source_status", "duplicate"),
    ("authority_class", "unlicensed"),
    ("text_mode", "text"),
])
def test_wrong_original_source_fails(field, bad):
    catalog = _catalog()
    catalog[field] = bad
    with pytest.raises(ValueError, match="authority"):
        review.audit_mm_angel("Deva", None, [], catalog)


def test_missing_catalog_or_unknown_monster_fails():
    with pytest.raises(ValueError):
        review.audit_mm_angel("Deva", None, [], None)
    with pytest.raises(ValueError):
        review.audit_mm_angel("Pseudo-deva", None, [], _catalog())


@pytest.mark.parametrize("field,bad", [
    ("classe_armatura", "18 (armatura naturale)"),
    ("punti_ferita", "137 (16d8 + 65)"),
    ("velocita", "9 m, volare 36 m"),
    ("grado_sfida", "11"),
    ("taglia", "Grande"),
])
def test_plausible_but_wrong_source_values_fail_closed(monkeypatch, field, bad):
    corrupted = deepcopy(review.ANGELS)
    corrupted["Deva"][field] = bad
    monkeypatch.setattr(review, "ANGELS", corrupted)
    with pytest.raises(ValueError, match="sealed"):
        review.audit_mm_angel("Deva", None, [], _catalog())


def test_statblock_has_six_abilities_from_original_images():
    for name in review.ANGELS:
        result = review.audit_mm_angel(name, None, [], _catalog())
        assert set(result["attributes"]["caratteristiche"]) == {
            "for", "des", "cos", "int", "sag", "car",
        }
