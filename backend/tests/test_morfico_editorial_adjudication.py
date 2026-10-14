"""Regression protections for registered Eberron Morfico translation typo."""

from copy import deepcopy

import pytest

from services.source_editorial_adjudications import (
    ENGLISH_CORRECTED_HP,
    EXPECTED_CORE_EXCERPT,
    EXPECTED_FLAGS,
    RECORD_ID,
    SEALED_ATTRIBUTES,
    SOURCE_CHECKSUM,
    assess_morfico_editorial_discrepancy,
)
from services.ocr_semantic_gates import HP_FORMAT_ERROR_FLAG, monster_semantic_numeric_flags


def _record():
    return {
        "id": RECORD_ID,
        "name": "Morfico",
        "reference_type": "monster",
        "review_status": "pending",
        "canonical_id": None,
        "source_text_checksum": SOURCE_CHECKSUM,
        "review_flags": list(EXPECTED_FLAGS),
        "attributes": dict(SEALED_ATTRIBUTES),
        "source_refs": [{
            "logical_source_id": "erlw_2019_it",
            "page": 321,
            "logical_page": 321,
            "filename": "618795464-Eberron.pdf",
            "source_status": "active",
            "source_role": "authority",
            "authority_class": "licensed_translation",
            "ruleset": "2014",
        }],
        "full_text": "Umanoide Medio (morfico) " + EXPECTED_CORE_EXCERPT,
    }


def test_morfico_editorial_review_recognizes_source_conflict_without_bypass():
    record = _record()
    result = assess_morfico_editorial_discrepancy(record)
    assert result["status"] == "eligible_for_source_editorial_adjudication"
    assert result["requires_explicit_editorial_review"] is True
    assert result["core_attributes"]["punti_ferita"] == ENGLISH_CORRECTED_HP
    assert record["attributes"]["punti_ferita"] == "19 (3d8 + 8)"
    assert monster_semantic_numeric_flags(record["attributes"]) == {HP_FORMAT_ERROR_FLAG}
    assert monster_semantic_numeric_flags(result["core_attributes"]) == set()


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("id", "ref_99999999999999999999999999999999"),
        ("name", "Morfico Pelle Bestiale"),
        ("review_status", "verified"),
        ("source_text_checksum", "00" * 32),
        ("review_flags", []),
        ("canonical_id", "canonical-1"),
        ("attributes", {**SEALED_ATTRIBUTES, "velocita": "12 m"}),
        ("attributes", {**SEALED_ATTRIBUTES, "punti_ferita": "19 (3d8 + 6)"}),
        ("full_text", "Testo diverso senza le statistiche originali"),
    ],
)
def test_morfico_editorial_review_fails_closed_on_any_record_drift(kind, value):
    record = _record()
    record[kind] = value
    with pytest.raises(ValueError):
        assess_morfico_editorial_discrepancy(record)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("page", 320),
        ("logical_source_id", "mpmm_2022_it"),
        ("source_role", "supplemental"),
        ("source_status", "inactive"),
        ("authority_class", "unverified"),
    ],
)
def test_morfico_editorial_review_fails_closed_on_provenance_drift(kind, value):
    record = deepcopy(_record())
    record["source_refs"][0][kind] = value
    with pytest.raises(ValueError):
        assess_morfico_editorial_discrepancy(record)
