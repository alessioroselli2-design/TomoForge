"""Fail-closed regression tests for Bigby Death Giant Shrouded One."""

import hashlib
from copy import deepcopy

import pytest

import services.death_giant_shrouded_source_review as source_review
from services.death_giant_shrouded_source_review import (
    ATTRS,
    AUTHORITY,
    RECORD_ID,
    SOURCE_CHECKSUM,
    SOURCE_FILE,
    assess_death_giant_shrouded_registered_source,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

# Synthetic fixture only: no licensed source prose committed to this repository.
SYNTHETIC_RAW = "Synthetic test description, not copyrighted manual text."


@pytest.fixture(autouse=True)
def replace_fixture_raw_hash(monkeypatch):
    monkeypatch.setattr(
        source_review,
        "RAW_SHA256",
        hashlib.sha256(SYNTHETIC_RAW.encode("utf-8")).hexdigest(),
    )


def candidate():
    return {
        "id": RECORD_ID,
        "name": "Gigante Della Morte Ammantato",
        "source_name": "Gigante Della Morte Ammantato",
        "reference_type": "monster",
        "source_language": "it",
        "source_key": SOURCE_FILE,
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": deepcopy(ATTRS),
        "source_attributes": {},
        "review_corrections": {},
        "source_refs": [deepcopy(AUTHORITY)],
        "full_text": SYNTHETIC_RAW,
        "source_full_text": SYNTHETIC_RAW,
    }


def test_exact_source_snapshot_passes_readonly_and_requires_statblock_relink():
    original = candidate()
    before = deepcopy(original)
    result = assess_death_giant_shrouded_registered_source(original)
    assert result["status"] == "eligible_source_relink_and_status_review"
    assert result["original_description_page"] == 156
    assert result["required_statblock_page"] == 155
    assert result["writes"] == 0
    assert not monster_semantic_numeric_flags(ATTRS)
    assert original == before


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("id", "ref_wrong"),
        ("name", "Gigante Della Morte Mietitore"),
        ("source_name", "other"),
        ("source_key", "other.pdf"),
        ("source_language", "en"),
        ("reference_type", "spell"),
        ("review_status", "verified"),
        ("canonical_id", "duplicate"),
        ("review_flags", []),
        ("source_text_checksum", "0" * 64),
        ("attributes", {**ATTRS, "classe_armatura": "18"}),
        ("attributes", {**ATTRS, "punti_ferita": "195 (17d12 + 84)"}),
        ("attributes", {**ATTRS, "velocita": "9 m"}),
        ("source_attributes", {"punti_ferita": "195"}),
        ("review_corrections", {"_source_changed": True}),
        ("full_text", "altered"),
        ("source_full_text", "altered"),
    ],
)
def test_changed_record_fails_closed(field, bad):
    record = candidate()
    record[field] = bad
    with pytest.raises(ValueError):
        assess_death_giant_shrouded_registered_source(record)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("page", 155),
        ("logical_page", 155),
        ("logical_source_id", "mpmm_2022_it"),
        ("filename", "another.pdf"),
        ("source_role", "secondary"),
        ("source_status", "retired"),
        ("ruleset", "2024"),
    ],
)
def test_unregistered_provenance_drift_fails_closed(field, bad):
    record = candidate()
    record["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        assess_death_giant_shrouded_registered_source(record)


def test_missing_or_duplicate_authority_fails_closed():
    record = candidate()
    record["source_refs"] = []
    with pytest.raises(ValueError):
        assess_death_giant_shrouded_registered_source(record)
    record["source_refs"] = [deepcopy(AUTHORITY), deepcopy(AUTHORITY)]
    with pytest.raises(ValueError):
        assess_death_giant_shrouded_registered_source(record)


def test_global_numeric_gate_not_relaxed():
    assert monster_semantic_numeric_flags(
        {**ATTRS, "punti_ferita": "195 (17d12 + 84)"}
    )


def test_description_digest_is_sha256_not_source_checksum():
    assert len(source_review.SOURCE_CHECKSUM) == 64
    assert source_review.SOURCE_CHECKSUM != hashlib.sha256(
        SYNTHETIC_RAW.encode("utf-8")
    ).hexdigest()
