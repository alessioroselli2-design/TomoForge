"""Fail-closed regression tests for Bigby Lince Gigante source adjudication."""
from copy import deepcopy
import pytest
from services.ocr_semantic_gates import HP_FORMAT_ERROR_FLAG, monster_semantic_numeric_flags
from services.lince_source_review import (
    ATTRIBUTES, ITALIAN_RAW, RECORD_ID, SOURCE_CHECKSUM,
    assess_lince_registered_source,
)

def _source_record():
    return {
        "id": RECORD_ID, "name": "Lince Gigante", "reference_type": "monster",
        "review_status": "pending", "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": dict(ATTRIBUTES), "full_text": ITALIAN_RAW,
        "source_refs": [{
            "page": 167, "logical_page": 167,
            "ruleset": "2014",
            "filename": "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf",
            "source_title": "Bigby Presenta: La Gloria dei Giganti",
            "source_role": "authority",
            "source_status": "active",
            "authority_class": "licensed_translation",
            "logical_source_id": "bgg_2023_it",
        }],
    }

def test_exact_original_accepted_without_mutation():
    row = _source_record()
    before = deepcopy(row)
    result = assess_lince_registered_source(row)
    assert result["status"] == "eligible_status_only_source_review"
    assert result["numeric_gates_passed"]
    assert result["registered_pages"] == [167]
    assert row == before
    assert monster_semantic_numeric_flags(row["attributes"]) == set()

@pytest.mark.parametrize(
    ("field", "bad"), [
        ("id", "ref_00000000000000000000000000000000"),
        ("name", "Lince non registrata"),
        ("reference_type", "other"),
        ("review_status", "verified"),
        ("canonical_id", "other"),
        ("review_flags", []),
        ("source_text_checksum", "0" * 64),
        ("attributes", {**ATTRIBUTES, "classe_armatura": "15"}),
        ("attributes", {**ATTRIBUTES, "punti_ferita": "22 (4d8 + 5)"}),
        ("attributes", {**ATTRIBUTES, "velocita": "12 m, scalare 9 m"}),
        ("full_text", "Folletto Medio, Classe Armatura 14"),
        ("source_refs", []),
    ],
)
def test_record_drift_rejected(field, bad):
    row = _source_record()
    row[field] = bad
    with pytest.raises(ValueError):
        assess_lince_registered_source(row)

@pytest.mark.parametrize(
    ("field", "bad"), [
        ("page", 166), ("logical_page", 100),
        ("source_status", "retired"), ("source_role", "supplementary"),
        ("logical_source_id", "erlw_2019_it"),
        ("filename", "other.pdf"), ("ruleset", "2024"),
        ("source_title", "Other manual"),
    ],
)
def test_provenance_drift_rejected(field, bad):
    row = _source_record()
    row["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        assess_lince_registered_source(row)

def test_math_gate_still_rejects_incoherent_hp():
    invalid = {**ATTRIBUTES, "punti_ferita": "22 (4d8 + 5)"}
    assert HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(invalid)
