"""Fail closed if an already verified record's original source has changed."""
from copy import deepcopy
import hashlib

import pytest

import services.mpmm_three_wrong_verified_stats_review as audit
from services.mpmm_three_wrong_verified_stats_review import (
    TARGETS, OWNER, authority, review_misattributed_stats,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

SOURCE_TEXT = "Purely synthetic regression description; not copyrighted statblock text. " * 5


@pytest.fixture(params=list(TARGETS))
def sealed(request, monkeypatch):
    name = request.param
    spec = TARGETS[name]
    clone = deepcopy(TARGETS)
    clone[name]["sha256"] = hashlib.sha256(SOURCE_TEXT.encode()).hexdigest()
    monkeypatch.setattr(audit, "TARGETS", clone)
    row = {
        "id": spec["id"], "user_id": OWNER, "name": name,
        "source_name": name, "normalized_name": name.casefold(),
        "reference_type": "monster", "review_status": "verified",
        "review_flags": [], "canonical_id": None,
        "source_key": spec["file"], "source_language": "it",
        "source_text_checksum": spec["checksum"],
        "attributes": deepcopy(spec["original_attrs"]),
        "source_attributes": deepcopy(spec["source_attrs"]),
        "review_corrections": {"_source_changed": True},
        "source_refs": authority(spec),
        "full_text": SOURCE_TEXT, "source_full_text": SOURCE_TEXT,
    }
    return name, row


def test_positive_exact_original_snapshot_proposes_stats_without_writes(sealed):
    name, row = sealed
    before = deepcopy(row)
    result = review_misattributed_stats(name, row)
    assert result["status"] == "eligible_exact_statblock_correction"
    assert result["writes"] == 0
    assert result["already_verified_but_wrong"] is True
    assert result["correct_attributes"] == TARGETS[name]["fixed_attrs"]
    assert not monster_semantic_numeric_flags(result["correct_attributes"])
    assert row == before


@pytest.mark.parametrize(("field", "bad"), [
    ("id", "wrong"), ("user_id", "other-user"),
    ("name", "Wrong Name"), ("source_name", "Wrong Name"),
    ("normalized_name", "wrong"), ("reference_type", "other"),
    ("review_status", "pending"), ("review_flags", ["ocr_da_verificare"]),
    ("canonical_id", "another"), ("source_key", "wrong.pdf"),
    ("source_language", "en"), ("source_text_checksum", "0"*64),
    ("attributes", {}), ("source_attributes", {}),
    ("review_corrections", {}), ("source_refs", []),
    ("full_text", "modified"), ("source_full_text", "modified"),
])
def test_drift_rejected_even_if_record_status_was_verified(sealed, field, bad):
    name, row = sealed
    row[field] = bad
    with pytest.raises(ValueError):
        review_misattributed_stats(name, row)


@pytest.mark.parametrize(("field", "bad"), [
    ("page", 3), ("logical_page", 6), ("filename", "wrong.pdf"),
    ("source_role", "secondary"), ("source_status", "inactive"),
    ("logical_source_id", "other"), ("authority_class", "unlicensed"),
])
def test_wrong_original_authority_page_rejected(sealed, field, bad):
    name, row = sealed
    row["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        review_misattributed_stats(name, row)


def test_extra_or_wrong_second_neogi_authority_page_rejected(sealed):
    name, row = sealed
    row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        review_misattributed_stats(name, row)


def test_wrong_entity_never_reuses_neighbor_values(sealed):
    _, row = sealed
    with pytest.raises(ValueError):
        review_misattributed_stats("Unregistered Monster", row)


def test_hp_original_dice_averages_and_math_are_strict():
    for spec in TARGETS.values():
        hp, count, sides, bonus = spec["dice"]
        assert (count * (sides + 1)) // 2 + bonus == hp
        altered = dict(spec["fixed_attrs"])
        altered["punti_ferita"] = f"{hp} ({count}d{sides} + {bonus + 1})"
        assert monster_semantic_numeric_flags(altered)
