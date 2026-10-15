"""Strict source-drift controls for four separate MPMM encounter creatures."""
from copy import deepcopy
import hashlib
import pytest
import services.mpmm_four_encounter_source_review as review
from services.mpmm_four_encounter_source_review import (
    SOURCE, USER, TARGETS, authority, assess_mpmm_existing_creature,
)

FAKE_RAW = "Synthetic monster description, not an excerpt from the licensed source. " * 5


@pytest.fixture(params=list(TARGETS))
def record(request, monkeypatch):
    name = request.param
    t = TARGETS[name]
    specs = deepcopy(TARGETS)
    specs[name]["raw_sha256"] = hashlib.sha256(FAKE_RAW.encode()).hexdigest()
    monkeypatch.setattr(review, "TARGETS", specs)
    return name, {
        "id": t["id"], "user_id": USER, "name": name, "source_name": name,
        "normalized_name": name.casefold().replace("'", " "),
        "reference_type": "other", "review_status": "needs_review",
        "review_flags": [], "canonical_id": None,
        "source_key": SOURCE, "source_language": "it",
        "source_text_checksum": t["checksum"],
        "review_corrections": {"_source_changed": True},
        "source_refs": [authority(t["page"], t["logical"])],
        "attributes": {}, "source_attributes": {},
        "full_text": FAKE_RAW, "source_full_text": FAKE_RAW,
    }


def test_original_exact_record_passes_without_writes(record):
    name, row = record
    previous = deepcopy(row)
    verdict = assess_mpmm_existing_creature(name, row)
    assert verdict["status"] == "eligible_existing_source_reclassification"
    assert verdict["writes"] == 0
    assert verdict["source_immutable"]
    assert verdict["proposed_attributes"] == TARGETS[name]["attrs"]
    assert row == previous


@pytest.mark.parametrize(("key", "bad"), [
    ("id", "wrong"), ("user_id", "wrong"),
    ("name", "other"), ("source_name", "other"),
    ("normalized_name", "other"), ("reference_type", "monster"),
    ("review_status", "verified"), ("review_flags", ["ocr_da_verificare"]),
    ("canonical_id", "duplicate"), ("source_key", "wrong.pdf"),
    ("source_language", "en"), ("source_text_checksum", "0"*64),
    ("attributes", {"classe_armatura": "16"}), ("source_attributes", {"punti_ferita": "20"}),
    ("review_corrections", {}), ("source_refs", []),
    ("full_text", "changed"), ("source_full_text", "changed"),
])
def test_any_drift_fails_closed(record, key, bad):
    name, row = record
    row[key] = bad
    with pytest.raises(ValueError):
        assess_mpmm_existing_creature(name, row)


@pytest.mark.parametrize(("key", "bad"), [
    ("page", 999), ("logical_page", 999), ("filename", "wrong.pdf"),
    ("logical_source_id", "bgg_2023_it"), ("ruleset", "2024"),
    ("authority_class", "unlicensed"), ("source_role", "secondary"),
])
def test_wrong_original_page_or_source_fails(record, key, bad):
    name, row = record
    row["source_refs"][0][key] = bad
    with pytest.raises(ValueError):
        assess_mpmm_existing_creature(name, row)


def test_no_wrong_entity_or_duplicate_provenance(record):
    name, row = record
    with pytest.raises(ValueError):
        assess_mpmm_existing_creature("Other Creature", row)
    row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        assess_mpmm_existing_creature(name, row)
