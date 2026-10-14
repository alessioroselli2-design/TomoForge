"""Regressions for the sealed Cacciatore Di Baphomet source review."""
from copy import deepcopy

import pytest

from services.ocr_semantic_gates import HP_FORMAT_ERROR_FLAG, monster_semantic_numeric_flags
from services.baphomet_source_review import (
    ATTRS, AUTHORITY, CHECKSUM, RAW, RECORD_ID, SOURCE_ATTRS, SOURCE_FILE,
    assess_baphomet_registered_source,
)


def record():
    return {
        "id": RECORD_ID, "name": "Cacciatore Di Baphomet",
        "reference_type": "monster", "source_language": "it",
        "source_key": SOURCE_FILE, "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": CHECKSUM,
        "attributes": deepcopy(ATTRS),
        "source_attributes": deepcopy(SOURCE_ATTRS),
        "full_text": RAW, "source_full_text": RAW,
        "source_refs": [deepcopy(AUTHORITY)],
    }


def test_original_is_eligible_and_unchanged():
    original = record()
    before = deepcopy(original)
    result = assess_baphomet_registered_source(original)
    assert result["status"] == "eligible_status_only_source_review"
    assert original == before
    assert not monster_semantic_numeric_flags(ATTRS)


@pytest.mark.parametrize(("field", "bad"), [
    ("id", "ref_wrong"), ("name", "Baphomet"),
    ("reference_type", "spell"), ("source_language", "en"),
    ("source_key", "other.pdf"), ("review_status", "verified"),
    ("canonical_id", "dup"), ("review_flags", []),
    ("source_text_checksum", "0" * 64),
    ("attributes", {**ATTRS, "classe_armatura": "18"}),
    ("attributes", {**ATTRS, "punti_ferita": "200 (16d12 + 95)"}),
    ("attributes", {**ATTRS, "velocita": "9 m"}),
    ("source_attributes", {**SOURCE_ATTRS, "classe_armatura": "17"}),
    ("full_text", RAW.replace("1 7", "17")),
    ("source_full_text", RAW.replace("6dl 2", "6d12")),
])
def test_modified_record_fails_closed(field, bad):
    candidate = record()
    candidate[field] = bad
    with pytest.raises(ValueError):
        assess_baphomet_registered_source(candidate)


@pytest.mark.parametrize(("field", "bad"), [
    ("page", 125), ("logical_page", 123),
    ("logical_source_id", "mpmm_2022_it"),
    ("filename", "other.pdf"), ("ruleset", "2024"),
    ("source_status", "retired"), ("source_role", "secondary"),
    ("authority_class", "unlicensed"),
])
def test_wrong_source_fails_closed(field, bad):
    candidate = record()
    candidate["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        assess_baphomet_registered_source(candidate)


def test_duplicate_and_absent_authority_blocked():
    candidate = record()
    candidate["source_refs"].append(deepcopy(AUTHORITY))
    with pytest.raises(ValueError):
        assess_baphomet_registered_source(candidate)
    candidate["source_refs"] = []
    with pytest.raises(ValueError):
        assess_baphomet_registered_source(candidate)


def test_global_math_gate_still_rejects_bad_hp():
    assert HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags({
        **ATTRS, "punti_ferita": "200 (16d12 + 95)"
    })
