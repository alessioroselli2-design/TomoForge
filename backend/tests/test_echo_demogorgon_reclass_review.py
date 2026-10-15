"""Regression tests: Bigby p130 Echo of Demogorgon, no canonical bypass."""
from copy import deepcopy
import hashlib

import pytest

import services.echo_demogorgon_reclass_review as review
from services.ocr_semantic_gates import monster_semantic_numeric_flags
from services.echo_demogorgon_reclass_review import (
    ATTRIBUTES, AUTHORITY, RECORD_ID, SOURCE, SOURCE_CHECKSUM,
    assess_existing_echo_record,
)
SYNTHETIC_DESCRIPTION = "Demogorgon " + "ettin " * 65


@pytest.fixture(autouse=True)
def mock_only_source_raw_hash(monkeypatch):
    monkeypatch.setattr(
        review, "RAW_SHA256",
        hashlib.sha256(SYNTHETIC_DESCRIPTION.encode("utf-8")).hexdigest(),
    )


def original():
    return {
        "id": RECORD_ID, "name": "Eco Di Demogorgon",
        "source_name": "Eco Di Demogorgon",
        "normalized_name": "eco di demogorgon",
        "reference_type": "other",
        "source_language": "it", "source_key": SOURCE,
        "review_status": "needs_review", "review_flags": [],
        "canonical_id": None, "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": {}, "source_attributes": {},
        "review_corrections": {"_source_changed": True},
        "source_refs": [deepcopy(AUTHORITY)],
        "full_text": SYNTHETIC_DESCRIPTION,
        "source_full_text": SYNTHETIC_DESCRIPTION,
    }


def test_source_locked_reclassification_candidate_is_readonly_and_valid():
    before = original()
    candidate = deepcopy(before)
    result = assess_existing_echo_record(candidate)
    assert result["status"] == "eligible_exact_record_reclassification"
    assert result["stats"] == ATTRIBUTES
    assert result["writes"] == 0
    assert before == candidate
    assert not monster_semantic_numeric_flags(ATTRIBUTES)


@pytest.mark.parametrize(
    ("key", "change"),
    [
        ("id", "wrong"), ("name", "Demogorgon"),
        ("source_name", "Demogorgon"),
        ("reference_type", "monster"),
        ("normalized_name", "demogorgon"),
        ("source_language", "en"), ("source_key", "wrong.pdf"),
        ("review_status", "verified"),
        ("review_flags", ["ocr_da_verificare"]),
        ("canonical_id", "linked"),
        ("source_text_checksum", "0" * 64),
        ("attributes", {"punti_ferita": "85"}),
        ("source_attributes", {"classe_armatura": "14"}),
        ("review_corrections", {}),
        ("full_text", "altered"),
        ("source_full_text", "altered"),
        ("source_refs", []),
    ],
)
def test_record_drift_blocks_reclassification(key, change):
    row = original()
    row[key] = change
    with pytest.raises(ValueError):
        assess_existing_echo_record(row)


@pytest.mark.parametrize(("key", "change"), [
    ("page", 131), ("logical_page", 129),
    ("logical_source_id", "mpmm_2022_it"),
    ("filename", "other.pdf"), ("ruleset", "2024"),
    ("source_role", "secondary"),
    ("source_status", "inactive"),
    ("authority_class", "not_licensed"),
])
def test_wrong_authority_blocks(key, change):
    row = original()
    row["source_refs"][0][key] = change
    with pytest.raises(ValueError):
        assess_existing_echo_record(row)


def test_no_duplicate_authority_or_corrupted_hp():
    row = original()
    row["source_refs"].append(deepcopy(AUTHORITY))
    with pytest.raises(ValueError):
        assess_existing_echo_record(row)
    assert monster_semantic_numeric_flags(
        {**ATTRIBUTES, "punti_ferita": "85 (10d10 + 31)"}
    )
