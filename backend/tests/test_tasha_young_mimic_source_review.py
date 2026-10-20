"""Tasha Young Mimic: immutable licensed source and anti-duplicate tests."""
import pytest
from services.tasha_young_mimic_source_review import (
    ATTRS, CATALOG_FILE, ID, NAME, PAGE, SOURCE_ID, audit_young_mimic,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags


def catalog():
    return {
        "logical_source_id": SOURCE_ID,
        "physical_filename": CATALOG_FILE,
        "physical_pages": 194,
        "source_status": "active",
        "authority_class": "licensed_translation",
        "source_role": "authority",
    }


def test_exact_source_is_eligible_without_writes():
    result = audit_young_mimic(None, [], catalog())
    assert result["status"] == "eligible_manual_visual_source_registration"
    assert result["record_id"] == ID
    assert result["page"] == PAGE
    assert result["name"] == NAME
    assert result["writes"] == 0
    assert result["automatic_ocr_not_claimed"]
    assert not monster_semantic_numeric_flags(ATTRS)


@pytest.mark.parametrize(("record_id", "names"), [
    ({"id": ID}, []), (None, [{"name": NAME}]),
    (None, [{"name": NAME, "reference_type": "other"}]),
])
def test_duplicate_or_same_name_is_rejected(record_id, names):
    with pytest.raises(ValueError):
        audit_young_mimic(record_id, names, catalog())


@pytest.mark.parametrize(("key", "invalid"), [
    ("logical_source_id", "mpmm_2022_it"),
    ("physical_filename", "wrong.pdf"),
    ("source_status", "retired"),
    ("authority_class", "unlicensed"),
    ("source_role", "extraction_aid"),
    ("physical_pages", 165),
    ("physical_pages", None),
])
def test_provenance_drift_fails_closed(key, invalid):
    data = catalog()
    data[key] = invalid
    with pytest.raises(ValueError):
        audit_young_mimic(None, [], data)


def test_missing_source_fails():
    with pytest.raises(ValueError):
        audit_young_mimic(None, [], None)


def test_corrupt_hit_dice_is_not_accepted_by_global_gate():
    assert monster_semantic_numeric_flags({**ATTRS, "punti_ferita": "7 (2d4 + 3)"})
