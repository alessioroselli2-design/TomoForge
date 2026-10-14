"""Single-record source proof; no broad OCR-gate changes allowed."""

from copy import deepcopy

import pytest

from services.ocr_semantic_gates import (
    HP_FORMAT_ERROR_FLAG,
    monster_semantic_numeric_flags,
)
from services.rak_tulkhesh_source_review import (
    ATTRIBUTES,
    ITALIAN_RAW,
    RECORD_ID,
    SOURCE_CHECKSUM,
    assess_rak_tulkhesh_registered_source,
)


def _original():
    return {
        "id": RECORD_ID,
        "name": "Rak Tulkhesh",
        "reference_type": "monster",
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": dict(ATTRIBUTES),
        "full_text": ITALIAN_RAW,
        "source_refs": [
            {
                "page": p,
                "logical_page": p,
                "logical_source_id": "erlw_2019_it",
                "source_status": "active",
                "source_role": "authority",
                "authority_class": "licensed_translation",
                "ruleset": "2014",
                "filename": "618795464-Eberron.pdf",
                "source_title": "Eberron: Rinascita dopo l’Ultima Guerra",
            }
            for p in (313, 314)
        ],
    }


def test_correct_source_and_original_attributes_are_preserved():
    original = _original()
    preserved = deepcopy(original)
    result = assess_rak_tulkhesh_registered_source(original)
    assert result["status"] == "eligible_status_only_source_review"
    assert result["numeric_gates_passed"] is True
    assert not monster_semantic_numeric_flags(original["attributes"])
    assert original == preserved
    assert "33dl2" in original["full_text"]


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("id", "ref_00000000000000000000000000000000"),
        ("name", "Another Fiend"),
        ("reference_type", "other"),
        ("canonical_id", "canonical_1"),
        ("review_status", "verified"),
        ("review_flags", []),
        ("source_text_checksum", "0" * 64),
        ("full_text", ITALIAN_RAW.replace("33dl2", "33d12")),
        ("attributes", {**ATTRIBUTES, "classe_armatura": "23"}),
        ("attributes", {**ATTRIBUTES, "punti_ferita": "478 (33d12 + 260)"}),
        ("attributes", {**ATTRIBUTES, "velocita": "15 m"}),
    ],
)
def test_wrong_registered_record_is_blocked(field, bad):
    original = _original()
    original[field] = bad
    with pytest.raises(ValueError):
        assess_rak_tulkhesh_registered_source(original)


@pytest.mark.parametrize(
    ("index", "field", "bad"),
    [
        (0, "page", 312),
        (1, "page", 315),
        (0, "logical_source_id", "bgg_2023_it"),
        (0, "logical_page", 250),
        (0, "source_status", "retired"),
        (1, "source_role", "secondary"),
        (1, "filename", "another.pdf"),
        (1, "authority_class", "unknown"),
    ],
)
def test_wrong_source_ref_is_blocked(index, field, bad):
    original = _original()
    original["source_refs"][index][field] = bad
    with pytest.raises(ValueError):
        assess_rak_tulkhesh_registered_source(original)


def test_missing_page_ref_is_blocked():
    original = _original()
    original["source_refs"].pop()
    with pytest.raises(ValueError):
        assess_rak_tulkhesh_registered_source(original)


def test_global_math_gate_still_rejects_wrong_dice():
    attrs = {**ATTRIBUTES, "punti_ferita": "478 (33d12 + 260)"}
    assert HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(attrs)
