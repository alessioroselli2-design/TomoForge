"""Fail-closed source-adjudication regressions for Tarkanan Assassin."""

from copy import deepcopy

import pytest

from services.ocr_semantic_gates import HP_FORMAT_ERROR_FLAG, monster_semantic_numeric_flags
from services.tarkanan_source_review import (
    ATTRIBUTES,
    ITALIAN_RAW,
    RECORD_ID,
    SOURCE_CHECKSUM,
    assess_tarkanan_registered_source,
)


def _original():
    return {
        "id": RECORD_ID,
        "name": "Assassino Tarkanan",
        "reference_type": "monster",
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": [],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": dict(ATTRIBUTES),
        "full_text": ITALIAN_RAW,
        "source_refs": [
            {
                "page": page,
                "logical_page": page,
                "ruleset": "2014",
                "filename": "618795464-Eberron.pdf",
                "source_role": "authority",
                "source_status": "active",
                "authority_class": "licensed_translation",
                "logical_source_id": "erlw_2019_it",
            }
            for page in (317, 318)
        ],
    }


def test_original_source_review_keeps_all_core_values_and_gates():
    before = _original()
    result = assess_tarkanan_registered_source(before)
    assert result["status"] == "eligible_status_only_source_review"
    assert result["original_attributes_unchanged"]
    assert result["numeric_gates_passed"]
    assert monster_semantic_numeric_flags(before["attributes"]) == set()
    assert before["review_status"] == "pending"


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("id", "ref_99999999999999999999999999999999"),
        ("name", "Tarkanan Alternative"),
        ("reference_type", "other"),
        ("review_status", "verified"),
        ("canonical_id", "canonical"),
        ("review_flags", ["ocr_da_verificare"]),
        ("source_text_checksum", "f" * 64),
        ("attributes", {**ATTRIBUTES, "velocita": "12 m"}),
        ("attributes", {**ATTRIBUTES, "classe_armatura": "16"}),
        ("attributes", {**ATTRIBUTES, "punti_ferita": "45 (7d8 + 12)"}),
        ("full_text", "not authentic source text"),
    ],
)
def test_any_record_drift_blocks_review(field, bad):
    record = _original()
    record[field] = bad
    with pytest.raises(ValueError):
        assess_tarkanan_registered_source(record)


@pytest.mark.parametrize(
    ("page_index", "field", "bad"),
    [
        (0, "page", 316),
        (1, "page", 319),
        (0, "logical_page", 111),
        (1, "source_status", "retired"),
        (0, "logical_source_id", "bgg_2023_it"),
        (1, "source_role", "supplementary"),
        (0, "filename", "other.pdf"),
    ],
)
def test_wrong_manual_or_physical_page_blocks(page_index, field, bad):
    record = deepcopy(_original())
    record["source_refs"][page_index][field] = bad
    with pytest.raises(ValueError):
        assess_tarkanan_registered_source(record)


def test_arithmetic_tampering_remains_blocked_by_global_gate():
    corrupted = {**ATTRIBUTES, "punti_ferita": "45 (7d8 + 12)"}
    assert HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(corrupted)
