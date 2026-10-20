"""Negative drift tests for registered Bigby Fomorian Nobile."""
import hashlib
from copy import deepcopy

import pytest

import services.fomorian_nobile_source_review as source
from services.fomorian_nobile_source_review import (
    ATTRS, AUTHORITY, CHECKSUM, RECORD_ID, SOURCE_FILE,
    assess_fomorian_nobile,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE_RAW = "Fomorian nobile original synthetic source. " * 12


@pytest.fixture(autouse=True)
def synthetic_digest(monkeypatch):
    monkeypatch.setattr(
        source, "RAW_SHA256",
        hashlib.sha256(FAKE_RAW.encode("utf-8")).hexdigest(),
    )


def original():
    return {
        "id": RECORD_ID, "name": "Fomorian Nobile",
        "source_name": "Fomorian Nobile", "normalized_name": "fomorian nobile",
        "reference_type": "other", "source_language": "it",
        "source_key": SOURCE_FILE, "review_status": "needs_review",
        "review_flags": [], "canonical_id": None, "attributes": {},
        "source_attributes": {}, "review_corrections": {"_source_changed": True},
        "source_text_checksum": CHECKSUM,
        "source_refs": [deepcopy(AUTHORITY)],
        "full_text": FAKE_RAW, "source_full_text": FAKE_RAW,
    }


def test_exact_candidate_passes_and_is_unchanged():
    row = original()
    before = deepcopy(row)
    outcome = assess_fomorian_nobile(row)
    assert outcome["status"] == "eligible_exact_record_reclassification"
    assert outcome["proposed_attributes"] == ATTRS
    assert outcome["writes"] == 0
    assert row == before
    assert not monster_semantic_numeric_flags(ATTRS)


@pytest.mark.parametrize(("field", "invalid"), [
    ("id", "ref_mismatch"),
    ("name", "Fomorian Vermeiena Delle Profondità"),
    ("source_name", "Fomorian"),
    ("normalized_name", "fomorian"),
    ("reference_type", "monster"), ("source_language", "en"),
    ("source_key", "other.pdf"), ("review_status", "verified"),
    ("review_flags", ["ocr_da_verificare"]), ("canonical_id", "duplicate"),
    ("source_text_checksum", "0" * 64),
    ("attributes", {"classe_armatura": "14"}),
    ("source_attributes", {"velocita": "9 m"}),
    ("review_corrections", {}),
    ("full_text", "altered"), ("source_full_text", "altered"),
    ("source_refs", []),
])
def test_drift_fails_closed(field, invalid):
    row = original()
    row[field] = invalid
    with pytest.raises(ValueError):
        assess_fomorian_nobile(row)


@pytest.mark.parametrize(("field", "invalid"), [
    ("page", 137), ("logical_page", 135), ("logical_source_id", "mpmm_2022_it"),
    ("filename", "wrong.pdf"), ("source_role", "secondary"),
    ("source_status", "retired"), ("authority_class", "unlicensed"),
    ("ruleset", "2024"),
])
def test_authority_provenance_drift(field, invalid):
    row = original()
    row["source_refs"][0][field] = invalid
    with pytest.raises(ValueError):
        assess_fomorian_nobile(row)


def test_duplicate_authority_and_invalid_hit_dice():
    row = original()
    row["source_refs"].append(deepcopy(AUTHORITY))
    with pytest.raises(ValueError):
        assess_fomorian_nobile(row)
    assert monster_semantic_numeric_flags({**ATTRS, "punti_ferita": "253 (22d12 + 111)"})
