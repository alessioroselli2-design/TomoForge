"""Regressions for exact Nuvola Spettrale source-review gates."""
from copy import deepcopy
import pytest
from services.ocr_semantic_gates import HP_FORMAT_ERROR_FLAG, monster_semantic_numeric_flags
from services.nuvola_source_review import (
    RECORD_ID, SOURCE_CHECKSUM, ITALIAN_RAW, ATTRIBUTES,
    assess_nuvola_registered_source,
)


def _record():
    return {
        "id": RECORD_ID, "name": "Nuvola Spettrale",
        "reference_type": "monster", "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": dict(ATTRIBUTES), "full_text": ITALIAN_RAW,
        "source_refs": [{
            "page": 168, "logical_page": 168, "logical_source_id": "bgg_2023_it",
            "source_role": "authority", "source_status": "active",
            "authority_class": "licensed_translation", "ruleset": "2014",
            "source_title": "Bigby Presenta: La Gloria dei Giganti",
            "filename": "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf",
        }],
    }


def test_exact_original_eligible_and_unchanged():
    record = _record()
    before = deepcopy(record)
    result = assess_nuvola_registered_source(record)
    assert result["status"] == "eligible_status_only_source_review"
    assert record == before
    assert not monster_semantic_numeric_flags(record["attributes"])


@pytest.mark.parametrize(("field", "wrong"), [
    ("id", "ref_00000000000000000000000000000000"),
    ("name", "wrong"), ("reference_type", "other"),
    ("review_status", "verified"), ("canonical_id", "duplicate"),
    ("review_flags", []), ("source_text_checksum", "0" * 64),
    ("full_text", ITALIAN_RAW.replace("18dl2", "18d12")),
    ("attributes", {**ATTRIBUTES, "classe_armatura": "16"}),
    ("attributes", {**ATTRIBUTES, "punti_ferita": "189 (18d12 + 70)"}),
    ("attributes", {**ATTRIBUTES, "velocita": "15 m"}),
])
def test_changed_record_is_blocked(field, wrong):
    record = _record()
    record[field] = wrong
    with pytest.raises(ValueError):
        assess_nuvola_registered_source(record)


@pytest.mark.parametrize(("field", "wrong"), [
    ("page", 182), ("logical_page", 184), ("logical_source_id", "erlw_2019_it"),
    ("source_role", "supplementary"), ("source_status", "retired"),
    ("ruleset", "2024"), ("filename", "unrelated.pdf"),
])
def test_changed_source_is_blocked(field, wrong):
    record = _record()
    record["source_refs"][0][field] = wrong
    with pytest.raises(ValueError):
        assess_nuvola_registered_source(record)


def test_duplicate_source_ref_blocked():
    record = _record()
    record["source_refs"].append(dict(record["source_refs"][0]))
    with pytest.raises(ValueError):
        assess_nuvola_registered_source(record)


def test_original_numeric_gate_rejects_bad_hp():
    assert HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags({
        **ATTRIBUTES, "punti_ferita": "189 (18d12 + 70)"
    })
