"""Demilich erratum: keep p48 Italian source and corrected d4 count separate."""
from copy import deepcopy

import pytest

from services import mm_demilich_official_errata_review as demilich
from services.ocr_semantic_gates import monster_semantic_numeric_flags


def catalog():
    return {
        "logical_source_id": demilich.SOURCE_ID,
        "physical_filename": demilich.FILENAME,
        "physical_sha256": demilich.SOURCE_SHA256,
        "physical_pages": demilich.SOURCE_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


def test_official_errata_reconciles_original_math_without_rewriting_source():
    r = demilich.audit(catalog())
    assert r["id"] == demilich.ID
    assert r["physical_page"] == 48
    assert r["source_attributes"]["punti_ferita"] == "80 (20d4)"
    assert r["attributes"]["punti_ferita"] == "80 (32d4)"
    assert r["source_text_checksum"] == demilich.ORIGINAL_SHA256
    assert r["canonical_excerpt_sha256"] == demilich.CANONICAL_SHA256
    assert r["review_corrections"]["punti_ferita"]["url"] == demilich.ERRATA_URL
    assert r["original_source_unchanged"] is True
    assert r["writes"] == 0
    assert not monster_semantic_numeric_flags(r["attributes"])
    assert monster_semantic_numeric_flags(r["source_attributes"])


def test_original_hp_average_does_not_agree_with_printed_80():
    assert 20 * 5 // 2 == 50
    assert 32 * 5 // 2 == 80


def test_duplicate_identity_fails():
    with pytest.raises(ValueError, match="duplicate"):
        demilich.audit(catalog(), record_exists=True)
    with pytest.raises(ValueError, match="duplicate"):
        demilich.audit(catalog(), monster_name_collisions=[{"name": "Demilich"}])


@pytest.mark.parametrize("field,changed", [
    ("physical_sha256", "0" * 64),
    ("physical_pages", 250),
    ("source_status", "duplicate"),
    ("source_role", "extraction_aid"),
])
def test_wrong_source_fails_closed(field, changed):
    bad = catalog()
    bad[field] = changed
    with pytest.raises(ValueError, match="source_drift"):
        demilich.audit(bad)


def test_plausible_but_unofficial_stats_fail(monkeypatch):
    monkeypatch.setattr(demilich, "CANONICAL_HP", "80 (20d4)")
    with pytest.raises(ValueError):
        demilich.audit(catalog())


def test_outputs_cannot_modify_sealed_source_data():
    old = deepcopy(demilich.ATTRIBUTES)
    r = demilich.audit(catalog())
    r["attributes"]["caratteristiche"]["for"] = "30"
    assert demilich.ATTRIBUTES == old
