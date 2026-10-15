"""Regression tests for the immutable registered Tasha Steel Defender source."""

import hashlib
from copy import deepcopy

import pytest

import services.tasha_steel_defender_source_review as source_review
from services.ocr_semantic_gates import monster_semantic_numeric_flags
from services.tasha_steel_defender_source_review import (
    ATTRS,
    CHECKSUM,
    HISTORICAL_OCR_ATTRS,
    HP_FORMULA,
    RECORD_ID,
    SOURCE_FILE,
    SOURCE_REF,
    assess_tasha_steel_defender_source,
)

# Synthetic scaffolding, not the original publisher's prose.
RAW_FIXTURE = (
    "Costrutto Medio Classe Armatura 15 (armatura naturale) "
    "Punti Ferita " + HP_FORMULA + " Velocità 12 m"
)


@pytest.fixture(autouse=True)
def fixture_digest(monkeypatch):
    monkeypatch.setattr(
        source_review,
        "RAW_SHA256",
        hashlib.sha256(RAW_FIXTURE.encode("utf-8")).hexdigest(),
    )


def record():
    return {
        "id": RECORD_ID,
        "name": "Difensore D'Acciaio",
        "source_name": "Difensore D'Acciaio",
        "reference_type": "monster",
        "source_language": "it",
        "source_key": SOURCE_FILE,
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": CHECKSUM,
        "attributes": deepcopy(ATTRS),
        "source_attributes": deepcopy(HISTORICAL_OCR_ATTRS),
        "review_corrections": {"_source_changed": True},
        "source_refs": [deepcopy(SOURCE_REF)],
        "full_text": RAW_FIXTURE,
        "source_full_text": RAW_FIXTURE,
    }


def test_unmodified_original_formula_eligible_and_preserved():
    before = record()
    candidate = deepcopy(before)
    result = assess_tasha_steel_defender_source(candidate)
    assert result["status"] == "eligible_source_locked_status_only_review"
    assert result["dynamic_hp_numeric_gate_passed"]
    assert result["writes"] == 0
    assert candidate == before
    assert not monster_semantic_numeric_flags(ATTRS)


@pytest.mark.parametrize(
    ("field", "altered"),
    [
        ("id", "ref_wrong"),
        ("name", "Difensore D'Acciaio alterato"),
        ("source_name", "Altra creatura"),
        ("reference_type", "other"),
        ("source_language", "en"),
        ("source_key", "other.pdf"),
        ("review_status", "verified"),
        ("canonical_id", "dup"),
        ("review_flags", []),
        ("source_text_checksum", "0" * 64),
        ("attributes", {**ATTRS, "classe_armatura": "16"}),
        ("attributes", {**ATTRS, "punti_ferita": "21 (4d8 + 3)"}),
        ("attributes", {**ATTRS, "velocita": "9 m"}),
        ("source_attributes", {**HISTORICAL_OCR_ATTRS, "punti_ferita": "20"}),
        ("review_corrections", {}),
        ("full_text", "arbitrary"),
        ("source_full_text", "arbitrary"),
    ],
)
def test_mutations_fail_closed(field, altered):
    changed = record()
    changed[field] = altered
    with pytest.raises(ValueError):
        assess_tasha_steel_defender_source(changed)


@pytest.mark.parametrize(
    ("field", "value"),
    [("page", 21), ("filename", "different.pdf")],
)
def test_registered_page_and_file_drift_fail_closed(field, value):
    changed = record()
    changed["source_refs"][0][field] = value
    with pytest.raises(ValueError):
        assess_tasha_steel_defender_source(changed)


def test_missing_or_duplicate_original_page_fails_closed():
    changed = record()
    changed["source_refs"] = []
    with pytest.raises(ValueError):
        assess_tasha_steel_defender_source(changed)
    changed["source_refs"] = [deepcopy(SOURCE_REF), deepcopy(SOURCE_REF)]
    with pytest.raises(ValueError):
        assess_tasha_steel_defender_source(changed)


def test_raw_digest_drift_fails_closed():
    source_review.RAW_SHA256 = "0" * 64
    with pytest.raises(ValueError):
        assess_tasha_steel_defender_source(record())


def test_other_hp_forms_do_not_bypass_global_gate():
    assert monster_semantic_numeric_flags(
        {**ATTRS, "punti_ferita": "2 + modif. Intelligenza + 5 lvl (dB)"}
    )
    assert not monster_semantic_numeric_flags(ATTRS)
