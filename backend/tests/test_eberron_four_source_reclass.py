"""Fail-closed tests for original Eberron four-record reclassification."""
import hashlib
from copy import deepcopy

import pytest

from services.ocr_semantic_gates import monster_semantic_numeric_flags
from services.eberron_four_source_reclass import (
    OWNER, SOURCE, TARGETS, authority, assess_eberron_reclass,
)

NAMES = tuple(TARGETS)


@pytest.fixture(params=NAMES)
def source_record(request, monkeypatch):
    name = request.param
    t = TARGETS[name]
    raw = "Synthetic nonpublisher narrative for " + name * 10
    monkeypatch.setitem(t, "hash", hashlib.sha256(raw.encode()).hexdigest())
    return name, {
        "id": t["id"], "user_id": OWNER,
        "name": name, "source_name": name,
        "normalized_name": name.casefold(),
        "source_language": "it", "source_key": SOURCE,
        "reference_type": "other", "review_status": t["status"],
        "review_flags": [], "canonical_id": None,
        "attributes": {}, "source_attributes": {},
        "review_corrections": deepcopy(t["corrections"]),
        "source_text_checksum": t["checksum"],
        "source_refs": [authority(t["page"])],
        "full_text": raw, "source_full_text": raw,
    }


def test_candidate_gate_returns_readonly_and_preserves_source(source_record):
    name, row = source_record
    before = deepcopy(row)
    result = assess_eberron_reclass(name, row)
    assert result["status"] == "eligible_existing_record_reclassification"
    assert result["writes"] == 0
    assert result["attributes"] == TARGETS[name]["attributes"]
    assert row == before
    assert not monster_semantic_numeric_flags(TARGETS[name]["attributes"])


@pytest.mark.parametrize(("field", "value"), [
    ("id", "wrong"), ("user_id", "wrong"),
    ("name", "Other"), ("source_name", "Other"),
    ("normalized_name", "other"), ("source_key", "other.pdf"),
    ("source_language", "en"), ("reference_type", "monster"),
    ("review_status", "pending"), ("review_flags", ["ocr_da_verificare"]),
    ("canonical_id", "duplicate"), ("source_text_checksum", "0"*64),
    ("attributes", {"velocita": "12 m"}),
    ("source_attributes", {"classe_armatura": "13"}),
    ("source_refs", []), ("full_text", "tampered"),
    ("source_full_text", "tampered"),
    ("review_corrections", {"error": True}),
])
def test_core_identity_and_original_source_mutations_fail(source_record, field, value):
    name, row = source_record
    row[field] = value
    with pytest.raises(ValueError):
        assess_eberron_reclass(name, row)


@pytest.mark.parametrize(("field", "value"), [
    ("page", 999), ("logical_page", 999),
    ("logical_source_id", "bgg_2023_it"), ("filename", "wrong.pdf"),
    ("source_role", "secondary"), ("source_status", "retired"),
    ("authority_class", "unlicensed"), ("ruleset", "2024"),
])
def test_any_wrong_authority_fails(source_record, field, value):
    name, row = source_record
    row["source_refs"][0][field] = value
    with pytest.raises(ValueError):
        assess_eberron_reclass(name, row)


def test_missing_source_or_duplicate_page_fails(source_record):
    name, row = source_record
    assert assess_eberron_reclass(name, row)["writes"] == 0
    row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        assess_eberron_reclass(name, row)


def test_cross_page_sul_khatesh_separate_from_rak_tulkhesh(source_record):
    name, row = source_record
    result = assess_eberron_reclass(name, row)
    if name == "Sul Khatesh":
        assert result["description_page"] == 314
        assert result["statblock_page"] == 315
        assert len(result["final_source_refs"]) == 2
    else:
        assert len(result["final_source_refs"]) == 1


def test_wrong_entity_and_bad_hp_dice_fail_closed(source_record):
    _, row = source_record
    with pytest.raises(ValueError):
        assess_eberron_reclass("Not the registered monster", row)
    for spec in TARGETS.values():
        hp, count, faces, mod = spec["dice"]
        assert count * (faces + 1) // 2 + mod == hp
        modified = f"{hp} ({count}d{faces} + {mod + 1})"
        assert monster_semantic_numeric_flags(
            {**spec["attributes"], "punti_ferita": modified}
        )
