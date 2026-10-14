"""Source-locked regression: Rampollo Di Grolantor, Bigby p170-171."""
from copy import deepcopy
import pytest
from services.ocr_semantic_gates import HP_FORMAT_ERROR_FLAG, monster_semantic_numeric_flags
from services.grolantor_source_review import (
    RECORD_ID, SOURCE_CHECKSUM, ATTRIBUTES, ITALIAN_RAW,
    assess_grolantor_registered_source,
)

def _record():
    return {
        "id": RECORD_ID, "name": "Rampollo Di Grolantor",
        "reference_type": "monster", "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": dict(ATTRIBUTES), "full_text": ITALIAN_RAW,
        "source_refs": [{
            "page": p, "logical_page": p,
            "ruleset": "2014",
            "filename": "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf",
            "source_title": "Bigby Presenta: La Gloria dei Giganti",
            "source_role": "authority", "source_status": "active",
            "authority_class": "licensed_translation",
            "logical_source_id": "bgg_2023_it",
        } for p in (170, 171)],
    }

def test_registered_source_passes_without_original_data_changes():
    row = _record()
    original = deepcopy(row)
    result = assess_grolantor_registered_source(row)
    assert result["status"] == "eligible_status_only_source_review"
    assert result["registered_pages"] == [170, 171]
    assert result["numeric_gates_passed"]
    assert row == original
    assert not monster_semantic_numeric_flags(row["attributes"])

@pytest.mark.parametrize(
    ("field", "bad"), [
        ("id", "ref_00000000000000000000000000000000"),
        ("name", "Another scion"),
        ("reference_type", "other"),
        ("review_status", "verified"),
        ("canonical_id", "linked"),
        ("review_flags", []),
        ("source_text_checksum", "f" * 64),
        ("attributes", {**ATTRIBUTES, "classe_armatura": "19"}),
        ("attributes", {**ATTRIBUTES, "punti_ferita": "402 (23d20 + 162)"}),
        ("attributes", {**ATTRIBUTES, "velocita": "12 m"}),
        ("full_text", "not licensed original"),
        ("source_refs", []),
    ],
)
def test_snapshot_drift_rejected(field, bad):
    row = _record()
    row[field] = bad
    with pytest.raises(ValueError):
        assess_grolantor_registered_source(row)

@pytest.mark.parametrize(
    ("index", "field", "bad"), [
        (0, "page", 169), (1, "page", 172),
        (0, "logical_page", 999), (1, "source_status", "retired"),
        (0, "logical_source_id", "erlw_2019_it"),
        (1, "source_role", "supplementary"),
        (0, "filename", "wrong.pdf"),
        (1, "ruleset", "2024"),
    ],
)
def test_wrong_source_page_or_authority_rejected(index, field, bad):
    row = _record()
    row["source_refs"][index][field] = bad
    with pytest.raises(ValueError):
        assess_grolantor_registered_source(row)

def test_math_gate_does_not_accept_false_dice():
    bad = {**ATTRIBUTES, "punti_ferita": "402 (23d20 + 160)"}
    assert HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(bad)
