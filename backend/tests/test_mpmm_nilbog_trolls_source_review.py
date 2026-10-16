"""Original MPMM source guard regression tests for Nilbog and two trolls."""
import hashlib
from copy import deepcopy

import pytest

import services.mpmm_nilbog_trolls_source_review as audit
from services.mpmm_nilbog_trolls_source_review import (
    TARGETS, SOURCE, USER, authority, inspect_existing_creature,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

SYNTHETIC = "A synthetic unit-test narrative; not licensed source prose. " * 8


@pytest.fixture(params=list(TARGETS))
def original(request, monkeypatch):
    name = request.param
    spec = TARGETS[name]
    test_targets = deepcopy(TARGETS)
    test_targets[name]["raw_sha256"] = hashlib.sha256(
        SYNTHETIC.encode("utf-8")
    ).hexdigest()
    monkeypatch.setattr(audit, "TARGETS", test_targets)
    row = {
        "id": spec["id"], "user_id": USER,
        "name": name, "source_name": name,
        "normalized_name": name.casefold(), "reference_type": "other",
        "review_status": "needs_review", "review_flags": [],
        "canonical_id": None, "source_language": "it",
        "source_key": SOURCE, "source_text_checksum": spec["checksum"],
        "attributes": {}, "source_attributes": {},
        "review_corrections": {"_source_changed": True},
        "source_refs": [authority(spec["page"], spec["logical_page"])],
        "full_text": SYNTHETIC, "source_full_text": SYNTHETIC,
    }
    return name, row


def test_exact_original_is_readonly_eligible(original):
    name, row = original
    before = deepcopy(row)
    verdict = inspect_existing_creature(name, row)
    assert verdict["status"] == "eligible_original_source_reclassification"
    assert verdict["attributes"] == TARGETS[name]["attrs"]
    assert verdict["writes"] == 0
    assert verdict["raw_preserved"] is True
    assert row == before
    assert not monster_semantic_numeric_flags(verdict["attributes"])


@pytest.mark.parametrize(("field", "bad"), [
    ("id", "wrong"), ("user_id", "another-user"),
    ("name", "Another"), ("source_name", "Another"),
    ("normalized_name", "another"), ("reference_type", "monster"),
    ("review_status", "verified"), ("review_flags", ["ocr_da_verificare"]),
    ("canonical_id", "other"), ("source_language", "en"),
    ("source_key", "wrong.pdf"), ("source_text_checksum", "0"*64),
    ("attributes", {"classe_armatura": "13"}), ("source_attributes", {"punti_ferita": "7"}),
    ("review_corrections", {}), ("source_refs", []),
    ("full_text", "changed"), ("source_full_text", "changed"),
])
def test_source_identity_and_data_drift_fails_closed(original, field, bad):
    name, row = original
    row[field] = bad
    with pytest.raises(ValueError):
        inspect_existing_creature(name, row)


@pytest.mark.parametrize(("field", "bad"), [
    ("page", 123), ("logical_page", 123),
    ("filename", "another.pdf"), ("source_role", "secondary"),
    ("source_status", "inactive"), ("logical_source_id", "unknown"),
    ("ruleset", "2024"), ("authority_class", "unlicensed"),
])
def test_registered_authority_drift_fails(original, field, bad):
    name, row = original
    row["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        inspect_existing_creature(name, row)


def test_cannot_reuse_neighboring_statblock(original):
    name, row = original
    row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        inspect_existing_creature(name, row)
    with pytest.raises(ValueError):
        inspect_existing_creature("A different monster", row)


def test_each_original_hp_average_and_strict_semantics():
    for spec in TARGETS.values():
        hp, count, faces, modifier = spec["dice"]
        assert (count*(faces+1))//2+modifier == hp
        attrs = dict(spec["attrs"])
        attrs["punti_ferita"] = f"{hp} ({count}d{faces} + {modifier+1})"
        assert monster_semantic_numeric_flags(attrs)
