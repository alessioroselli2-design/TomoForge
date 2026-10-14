"""Only the exact registered Chiamaburrasche snapshot is eligible."""

from copy import deepcopy

import pytest

from services.chiamaburrasche_source_review import (
    ATTRIBUTES,
    ITALIAN_RAW,
    RECORD_ID,
    SOURCE_CHECKSUM,
    assess_chiamaburrasche_registered_source,
)
from services.ocr_semantic_gates import HP_FORMAT_ERROR_FLAG, monster_semantic_numeric_flags


def _record():
    return {
        "id": RECORD_ID,
        "name": "Chiamaburrasche",
        "reference_type": "monster",
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": dict(ATTRIBUTES),
        "full_text": ITALIAN_RAW,
        "source_refs": [{
            "page": 154,
            "logical_page": 154,
            "logical_source_id": "bgg_2023_it",
            "source_status": "active",
            "source_role": "authority",
            "authority_class": "licensed_translation",
            "filename": "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf",
            "source_title": "Bigby Presenta: La Gloria dei Giganti",
            "ruleset": "2014",
        }],
    }


def test_exact_record_is_read_only_eligible():
    record = _record()
    saved = deepcopy(record)
    result = assess_chiamaburrasche_registered_source(record)
    assert result["status"] == "eligible_status_only_source_review"
    assert result["numeric_gates_passed"]
    assert result["raw_dice_text_preserved"]
    assert not monster_semantic_numeric_flags(record["attributes"])
    assert record == saved
    assert "27d l 2 + 1 35" in record["full_text"]


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("id", "ref_00000000000000000000000000000000"),
        ("name", "Different Giant"),
        ("reference_type", "other"),
        ("review_status", "verified"),
        ("canonical_id", "canonical_123"),
        ("review_flags", []),
        ("source_text_checksum", "0" * 64),
        ("full_text", ITALIAN_RAW.replace("27d l 2", "27d12")),
        ("attributes", {**ATTRIBUTES, "classe_armatura": "18"}),
        ("attributes", {**ATTRIBUTES, "punti_ferita": "310 (27d12 + 134)"}),
        ("attributes", {**ATTRIBUTES, "velocita": "12 m"}),
    ],
)
def test_any_record_or_stat_drift_blocks(field, changed):
    record = _record()
    record[field] = changed
    with pytest.raises(ValueError):
        assess_chiamaburrasche_registered_source(record)


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("page", 155),
        ("logical_page", 155),
        ("logical_source_id", "erlw_2019_it"),
        ("source_status", "retired"),
        ("source_role", "secondary"),
        ("authority_class", "unverified"),
        ("filename", "other.pdf"),
        ("source_title", "Different manual"),
        ("ruleset", "2024"),
    ],
)
def test_registered_source_drift_blocks(field, changed):
    record = _record()
    record["source_refs"][0][field] = changed
    with pytest.raises(ValueError):
        assess_chiamaburrasche_registered_source(record)


def test_multiple_sources_are_not_accepted():
    record = _record()
    record["source_refs"].append(dict(record["source_refs"][0]))
    with pytest.raises(ValueError):
        assess_chiamaburrasche_registered_source(record)


def test_invalid_hp_math_still_fails_global_gate():
    bad = {**ATTRIBUTES, "punti_ferita": "310 (27d12 + 134)"}
    assert HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(bad)
