"""Source-only Dyrrn review fails closed against provenance or HP drift."""

from copy import deepcopy

import pytest

from services.ocr_semantic_gates import (
    HP_FORMAT_ERROR_FLAG,
    monster_semantic_numeric_flags,
)
from services.dyrrn_source_review import (
    ATTRIBUTES,
    ITALIAN_RAW,
    RECORD_ID,
    SOURCE_CHECKSUM,
    assess_dyrrn_registered_source,
)


def _record():
    return {
        "id": RECORD_ID,
        "name": "Dyrrn",
        "reference_type": "monster",
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
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
                "source_title": "Eberron: Rinascita dopo l’Ultima Guerra",
            }
            for page in (289, 291)
        ],
    }


def test_exact_source_passes_without_changes():
    record = _record()
    preserved = deepcopy(record)
    report = assess_dyrrn_registered_source(record)
    assert report["status"] == "eligible_status_only_source_review"
    assert report["numeric_gates_passed"] is True
    assert report["raw_ocr_dice_is_preserved"] is True
    assert not monster_semantic_numeric_flags(record["attributes"])
    assert record == preserved
    assert "3ld8" in record["full_text"]


@pytest.mark.parametrize(
    ("field", "altered"),
    [
        ("id", "ref_00000000000000000000000000000000"),
        ("name", "Other Dyrrn"),
        ("review_status", "verified"),
        ("canonical_id", "canonical_abc"),
        ("reference_type", "other"),
        ("review_flags", []),
        ("source_text_checksum", "0" * 64),
        ("full_text", ITALIAN_RAW.replace("3ld8", "31d8")),
        ("attributes", {**ATTRIBUTES, "punti_ferita": "325 (31d8 + 185)"}),
        ("attributes", {**ATTRIBUTES, "classe_armatura": "22"}),
        ("attributes", {**ATTRIBUTES, "velocita": "15 m"}),
    ],
)
def test_any_registered_core_drift_rejected(field, altered):
    record = _record()
    record[field] = altered
    with pytest.raises(ValueError):
        assess_dyrrn_registered_source(record)


@pytest.mark.parametrize(
    ("index", "field", "altered"),
    [
        (0, "page", 288),
        (1, "page", 290),
        (0, "logical_page", 123),
        (0, "logical_source_id", "bgg_2023_it"),
        (0, "source_status", "retired"),
        (1, "source_role", "secondary"),
        (1, "filename", "other.pdf"),
        (0, "authority_class", "unknown"),
        (1, "source_title", "different manual"),
    ],
)
def test_registered_authority_drift_rejected(index, field, altered):
    record = _record()
    record["source_refs"][index][field] = altered
    with pytest.raises(ValueError):
        assess_dyrrn_registered_source(record)


def test_missing_source_page_rejected():
    record = _record()
    record["source_refs"].pop()
    with pytest.raises(ValueError):
        assess_dyrrn_registered_source(record)


def test_global_hp_math_gate_not_weakend():
    malformed = {**ATTRIBUTES, "punti_ferita": "325 (31d8 + 185)"}
    assert HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(malformed)
