"""Fail-closed regression tests for five distinct Bigby Italian stat blocks."""
import hashlib
from copy import deepcopy

import pytest

from services.ocr_semantic_gates import monster_semantic_numeric_flags
from services.bigby_five_source_reclass import (
    SOURCE, USER_ID, SPECS, authority, assess_bigby_reclassification,
)

NAMES = tuple(SPECS)


@pytest.fixture(params=NAMES)
def sealed_record(request, monkeypatch):
    name = request.param
    spec = SPECS[name]
    dummy_source = "Synthetic source description for " + name * 10
    monkeypatch.setitem(
        spec, "raw_sha256",
        hashlib.sha256(dummy_source.encode("utf-8")).hexdigest(),
    )
    record = {
        "id": spec["id"], "user_id": USER_ID,
        "name": name, "source_name": name,
        "normalized_name": name.casefold(),
        "reference_type": "other", "source_language": "it",
        "source_key": SOURCE, "review_status": spec["status"],
        "review_flags": [], "canonical_id": None,
        "attributes": {}, "source_attributes": {},
        "source_text_checksum": spec["checksum"],
        "review_corrections": deepcopy(spec["corrections"]),
        "source_refs": [authority(spec["page"])],
        "full_text": dummy_source, "source_full_text": dummy_source,
    }
    return name, record


def test_source_record_reclassifiable_readonly(sealed_record):
    name, row = sealed_record
    initial = deepcopy(row)
    result = assess_bigby_reclassification(name, row)
    assert row == initial
    assert result["status"] == "eligible_exact_record_reclassification"
    assert result["writes"] == 0
    assert result["proposed_attributes"] == SPECS[name]["attrs"]
    assert result["append_statblock_authority"] == (
        SPECS[name]["stats_page"] != SPECS[name]["page"]
    )
    assert not monster_semantic_numeric_flags(SPECS[name]["attrs"])


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("id", "ref_wrong"),
        ("user_id", "wrong_user"),
        ("name", "Other monster"),
        ("source_name", "Other monster"),
        ("normalized_name", "other monster"),
        ("reference_type", "monster"),
        ("source_language", "en"),
        ("source_key", "wrong.pdf"),
        ("review_status", "pending"),
        ("review_flags", ["ocr_da_verificare"]),
        ("canonical_id", "duplicate"),
        ("attributes", {"punti_ferita": "100"}),
        ("source_attributes", {"velocita": "18 m"}),
        ("source_text_checksum", "0" * 64),
        ("full_text", ""),
        ("source_full_text", "tampered"),
        ("source_refs", []),
    ],
)
def test_registered_snapshot_mutation_fails(sealed_record, field, bad):
    name, row = sealed_record
    row[field] = bad
    with pytest.raises(ValueError):
        assess_bigby_reclassification(name, row)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("page", 10), ("logical_page", 10),
        ("ruleset", "2024"), ("filename", "other.pdf"),
        ("source_role", "secondary"), ("source_status", "retired"),
        ("authority_class", "unlicensed"),
        ("logical_source_id", "mpmm_2022_it"),
    ],
)
def test_authority_must_match_original_page(sealed_record, field, bad):
    name, row = sealed_record
    row["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        assess_bigby_reclassification(name, row)


def test_exact_review_corrections_and_single_authority(sealed_record):
    name, row = sealed_record
    row["review_corrections"] = {"_changed": True}
    with pytest.raises(ValueError):
        assess_bigby_reclassification(name, row)
    row["review_corrections"] = deepcopy(SPECS[name]["corrections"])
    row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        assess_bigby_reclassification(name, row)


def test_unregistered_entity_fails(sealed_record):
    _, row = sealed_record
    with pytest.raises(ValueError):
        assess_bigby_reclassification("Different Monster", row)


def test_strict_hit_dice_gate_is_not_weakened():
    for spec in SPECS.values():
        hp, dice, sides, bonus = spec["dice"]
        assert dice * (sides + 1) // 2 + bonus == hp
        assert monster_semantic_numeric_flags(
            {**spec["attrs"], "punti_ferita": f"{hp} ({dice}d{sides} + {bonus + 1})"}
        )


def test_cross_page_titans_never_read_neighboring_crib_statblocks():
    surtur = SPECS["Rampollo Di Surtur"]
    thrym = SPECS["Rampollo Di Thrym"]
    assert (surtur["page"], surtur["stats_page"]) == (178, 179)
    assert (thrym["page"], thrym["stats_page"]) == (180, 181)
    assert surtur["attrs"]["punti_ferita"] != "555 (30d20 + 240)"
    assert thrym["attrs"]["classe_armatura"] != "20 (armatura naturale)"
