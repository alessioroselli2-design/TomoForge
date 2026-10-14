"""Isolated review requires exact official-source Steel Defender evidence."""

from copy import deepcopy

import pytest

from services.ocr_semantic_gates import monster_semantic_numeric_flags
from services.steel_defender_source_review import (
    RECORD_ID,
    SEALED_ATTRIBUTES,
    SEALED_FULL_TEXT,
    SOURCE_CHECKSUM,
    assess_steel_defender_source_review,
)


def _sealed_record():
    return {
        "id": RECORD_ID,
        "name": "Difensore D'Acciaio",
        "reference_type": "monster",
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": dict(SEALED_ATTRIBUTES),
        "full_text": SEALED_FULL_TEXT,
        "source_refs": [{
            "logical_source_id": "erlw_2019_it",
            "page": 62,
            "logical_page": 62,
            "source_status": "active",
            "source_role": "authority",
            "authority_class": "licensed_translation",
            "filename": "618795464-Eberron.pdf",
            "ruleset": "2014",
        }],
    }


def test_source_review_preserves_all_steel_defender_attributes_and_hp_gate():
    record = _sealed_record()
    result = assess_steel_defender_source_review(record)
    assert result["status"] == "eligible_status_only_source_review"
    assert result["attributes_unchanged"]
    assert result["numeric_gates_active_and_passed"]
    assert monster_semantic_numeric_flags(record["attributes"]) == set()
    assert record["review_status"] == "pending"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("id", "ref_a0000000000000000000000000000000"),
        ("name", "Difensore D'Acciaio Tasha"),
        ("reference_type", "other"),
        ("review_status", "verified"),
        ("canonical_id", "linked-record"),
        ("review_flags", []),
        ("source_text_checksum", "0" * 64),
        ("attributes", {**SEALED_ATTRIBUTES, "velocita": "9 m"}),
        ("attributes", {**SEALED_ATTRIBUTES, "punti_ferita": "22 (4d8 + 4)"}),
        ("full_text", "Missing registered source text"),
    ],
)
def test_any_record_content_drift_fails_closed(key, value):
    record = _sealed_record()
    record[key] = value
    with pytest.raises(ValueError):
        assess_steel_defender_source_review(record)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("page", 63),
        ("logical_page", 61),
        ("filename", "different.pdf"),
        ("logical_source_id", "mpmm_2022_it"),
        ("source_status", "inactive"),
        ("source_role", "supplement"),
        ("ruleset", "2024"),
    ],
)
def test_any_source_provenance_drift_fails_closed(key, value):
    record = deepcopy(_sealed_record())
    record["source_refs"][0][key] = value
    with pytest.raises(ValueError):
        assess_steel_defender_source_review(record)
