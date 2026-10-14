"""Exact-source Karrnathi review must fail closed on every meaningful drift."""

from copy import deepcopy

import pytest

from services.ocr_semantic_gates import HP_FORMAT_ERROR_FLAG, monster_semantic_numeric_flags
from services.karrnathi_source_review import (
    ATTRIBUTES,
    ITALIAN_RAW,
    RECORD_ID,
    SOURCE_CHECKSUM,
    assess_karrnathi_registered_source,
)


def _snapshot():
    return {
        "id": RECORD_ID,
        "name": "Non Morto Karrnathi",
        "reference_type": "monster",
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": [],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": dict(ATTRIBUTES),
        "full_text": ITALIAN_RAW,
        "source_refs": [
            {
                "page": 316,
                "logical_page": 316,
                "ruleset": "2014",
                "filename": "618795464-Eberron.pdf",
                "source_role": "authority",
                "source_status": "active",
                "authority_class": "licensed_translation",
                "logical_source_id": "erlw_2019_it",
                "source_title": "Eberron: Rinascita dopo l’Ultima Guerra",
            }
        ],
    }


def test_registered_source_passes_without_any_mutation():
    original = _snapshot()
    frozen = deepcopy(original)
    result = assess_karrnathi_registered_source(original)
    assert result["status"] == "eligible_status_only_source_review"
    assert result["numeric_gates_passed"] is True
    assert result["original_attributes_unchanged"] is True
    assert original == frozen
    assert not monster_semantic_numeric_flags(original["attributes"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "ref_00000000000000000000000000000000"),
        ("name", "Karrnathi Something"),
        ("reference_type", "other"),
        ("review_status", "verified"),
        ("canonical_id", "canonical_123"),
        ("review_flags", ["ocr_da_verificare"]),
        ("source_text_checksum", "0" * 64),
        ("full_text", "unregistered source"),
        ("attributes", {**ATTRIBUTES, "classe_armatura": "18"}),
        ("attributes", {**ATTRIBUTES, "velocita": "12 m"}),
        ("attributes", {**ATTRIBUTES, "punti_ferita": "52 (7d8 + 20)"}),
    ],
)
def test_wrong_record_or_core_is_blocked(field, value):
    record = _snapshot()
    record[field] = value
    with pytest.raises(ValueError):
        assess_karrnathi_registered_source(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("page", 315),
        ("logical_page", 317),
        ("logical_source_id", "bgg_2023_it"),
        ("filename", "wrong.pdf"),
        ("source_status", "retired"),
        ("source_role", "supplementary"),
        ("authority_class", "unknown"),
        ("source_title", "Unrelated Manual"),
        ("ruleset", "2024"),
    ],
)
def test_source_provenance_must_match(field, value):
    record = _snapshot()
    record["source_refs"][0][field] = value
    with pytest.raises(ValueError):
        assess_karrnathi_registered_source(record)


def test_multiple_sources_rejected():
    record = _snapshot()
    record["source_refs"].append(dict(record["source_refs"][0]))
    with pytest.raises(ValueError):
        assess_karrnathi_registered_source(record)


def test_global_hit_dice_math_remains_active():
    corrupted = {**ATTRIBUTES, "punti_ferita": "52 (7d8 + 20)"}
    assert HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(corrupted)
