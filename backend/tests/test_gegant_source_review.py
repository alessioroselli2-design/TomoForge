"""Regression and drift controls for the registered-source Gegant adjudication."""

from copy import deepcopy

import pytest

from services.gegant_source_review import (
    ATTRS,
    AUTHORITY,
    CHECKSUM,
    RAW,
    RECORD_ID,
    SOURCE_ATTRS,
    SOURCE_FILE,
    assess_gegant_registered_source,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags


def sealed_record():
    return {
        "id": RECORD_ID,
        "name": "Gegant",
        "source_name": "Gegant",
        "reference_type": "monster",
        "source_language": "it",
        "source_key": SOURCE_FILE,
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": CHECKSUM,
        "attributes": deepcopy(ATTRS),
        "source_attributes": deepcopy(SOURCE_ATTRS),
        "full_text": RAW,
        "source_full_text": RAW,
        "source_refs": [deepcopy(AUTHORITY)],
        "review_corrections": {"_source_changed": True},
    }


def test_original_eligible_and_unchanged():
    candidate = sealed_record()
    before = deepcopy(candidate)
    result = assess_gegant_registered_source(candidate)
    assert result["status"] == "eligible_status_only_source_review"
    assert result["writes"] == 0
    assert result["numeric_gates_passed"]
    assert candidate == before
    assert not monster_semantic_numeric_flags(ATTRS)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("id", "ref_wrong"),
        ("name", "Gigante"),
        ("source_name", "Gigant"),
        ("reference_type", "spell"),
        ("source_language", "en"),
        ("source_key", "another.pdf"),
        ("review_status", "verified"),
        ("canonical_id", "duplicate"),
        ("review_flags", []),
        ("review_corrections", {}),
        ("source_text_checksum", "0" * 64),
        ("attributes", {**ATTRS, "classe_armatura": "18 (armatura naturale)"}),
        ("attributes", {**ATTRS, "punti_ferita": "325 (21d20 + 104)"}),
        ("attributes", {**ATTRS, "velocita": "12 m"}),
        ("source_attributes", {**SOURCE_ATTRS, "punti_ferita": "325 (21d20 + 105)"}),
        ("full_text", RAW.replace("2l d20", "21d20")),
        ("source_full_text", RAW.replace("1 05", "105")),
    ],
)
def test_drift_fails_closed(field, bad):
    candidate = sealed_record()
    candidate[field] = bad
    with pytest.raises(ValueError):
        assess_gegant_registered_source(candidate)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("page", 143),
        ("logical_page", 141),
        ("logical_source_id", "mpmm_2022_it"),
        ("ruleset", "2024"),
        ("filename", "other.pdf"),
        ("source_role", "secondary"),
        ("source_status", "retired"),
        ("authority_class", "unlicensed"),
    ],
)
def test_wrong_authority_fails_closed(field, bad):
    candidate = sealed_record()
    candidate["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        assess_gegant_registered_source(candidate)


def test_missing_or_duplicate_authority_fails_closed():
    candidate = sealed_record()
    candidate["source_refs"] = []
    with pytest.raises(ValueError):
        assess_gegant_registered_source(candidate)
    candidate["source_refs"] = [deepcopy(AUTHORITY), deepcopy(AUTHORITY)]
    with pytest.raises(ValueError):
        assess_gegant_registered_source(candidate)


def test_global_numeric_gate_stays_strict():
    assert monster_semantic_numeric_flags(
        {**ATTRS, "punti_ferita": "325 (21d20 + 104)"}
    )
