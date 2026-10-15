"""Regression tests for a strictly new Eberron source-specific monster."""
from copy import deepcopy

import pytest

from services.eberron_valenar_steed_source_review import (
    ATTRIBUTES, DIGEST, EXCERPT, ID, NAME, PAGE, SOURCE, SOURCE_ID,
    validate_valenar_source,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags


def licensed_source():
    return {
        "logical_source_id": SOURCE_ID,
        "physical_filename": SOURCE,
        "physical_pages": 322,
        "source_status": "active",
        "authority_class": "licensed_translation",
        "source_role": "authority",
    }


def test_absent_exact_record_with_licensed_source_is_readonly_eligible():
    source = licensed_source()
    before = deepcopy(source)
    verdict = validate_valenar_source(None, [], source)
    assert verdict["status"] == "eligible_new_source_record_review"
    assert verdict["writes"] == 0
    assert verdict["id"] == ID
    assert verdict["source_page"] == PAGE
    assert verdict["name"] == NAME
    assert verdict["attributes"] == ATTRIBUTES
    assert len(DIGEST) == 64 and EXCERPT.startswith("Folletto Grande")
    assert source == before
    assert not monster_semantic_numeric_flags(ATTRIBUTES)


def test_duplicates_and_id_collisions_are_blocked():
    for existing_id, existing_name in [
        ({"id": ID}, []),
        (None, [{"name": NAME, "reference_type": "other"}]),
        (None, [{"name": NAME, "reference_type": "monster"}]),
    ]:
        with pytest.raises(ValueError):
            validate_valenar_source(existing_id, existing_name, licensed_source())


@pytest.mark.parametrize(("key", "invalid"), [
    ("logical_source_id", "bgg_2023_it"),
    ("physical_filename", "different.pdf"),
    ("physical_pages", 284),
    ("physical_pages", None),
    ("source_status", "retired"),
    ("authority_class", "unlicensed"),
    ("source_role", "secondary"),
])
def test_wrong_or_missing_registered_authority_fails(key, invalid):
    record = licensed_source()
    record[key] = invalid
    with pytest.raises(ValueError):
        validate_valenar_source(None, [], record)


def test_no_source_fails():
    with pytest.raises(ValueError):
        validate_valenar_source(None, [], None)
