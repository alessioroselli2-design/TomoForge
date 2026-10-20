"""Per-monster original-source and numeric drift tests: five Bigby statblocks."""
from copy import deepcopy
import hashlib

import pytest

import services.bigby_five_reclass_review as source
from services.bigby_five_reclass_review import (
    SOURCE, TARGETS, assess_bigby_registered_other, authority,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE_RAW = "Synthetic narrative for unit test; no licensed Bigby text." * 8


def record(record_id):
    info = source.TARGETS[record_id]
    return {
        "id": record_id, "name": info["name"], "source_name": info["name"],
        "normalized_name": info["name"].casefold(),
        "reference_type": "other", "review_status": info["status"],
        "source_language": "it", "source_key": SOURCE,
        "canonical_id": None, "review_flags": [],
        "source_text_checksum": info["checksum"],
        "source_refs": [authority(info["page"])],
        "attributes": {}, "source_attributes": {},
        "review_corrections": deepcopy(info["corrections"]),
        "full_text": FAKE_RAW, "source_full_text": FAKE_RAW,
    }


@pytest.fixture(autouse=True)
def fixture_hashes(monkeypatch):
    targets = deepcopy(TARGETS)
    for value in targets.values():
        value["raw_hash"] = hashlib.sha256(FAKE_RAW.encode("utf-8")).hexdigest()
    monkeypatch.setattr(source, "TARGETS", targets)


@pytest.mark.parametrize("target_id", list(TARGETS))
def test_individual_candidate_is_readonly_original_source_locked(target_id):
    candidate = record(target_id)
    initial = deepcopy(candidate)
    result = assess_bigby_registered_other(candidate, target_id)
    assert result["status"] == "eligible_single_record_reclassification"
    assert result["proposed_attributes"] == TARGETS[target_id]["attrs"]
    assert result["narrative_page"] == TARGETS[target_id]["page"]
    assert result["statblock_page"] == TARGETS[target_id]["stat_page"]
    assert result["writes"] == 0
    assert candidate == initial
    assert not monster_semantic_numeric_flags(result["proposed_attributes"])


@pytest.mark.parametrize("target_id", list(TARGETS))
@pytest.mark.parametrize(("field", "bad"), [
    ("reference_type", "monster"), ("review_status", "pending"),
    ("source_key", "other.pdf"), ("source_language", "en"),
    ("source_refs", []), ("attributes", {"classe_armatura": "17"}),
    ("source_attributes", {"punti_ferita": "20"}),
    ("review_flags", ["ocr_da_verificare"]), ("canonical_id", "duplicate"),
    ("source_text_checksum", "0" * 64),
    ("full_text", "changed"), ("source_full_text", "changed"),
])
def test_changed_record_fails_closed(target_id, field, bad):
    value = record(target_id)
    value[field] = bad
    with pytest.raises(ValueError):
        assess_bigby_registered_other(value, target_id)


@pytest.mark.parametrize("target_id", list(TARGETS))
def test_name_identity_checksum_and_original_corrections_are_sealed(target_id):
    for field in ("name", "source_name", "normalized_name", "review_corrections"):
        value = record(target_id)
        value[field] = "wrong"
        with pytest.raises(ValueError):
            assess_bigby_registered_other(value, target_id)


@pytest.mark.parametrize("target_id", list(TARGETS))
def test_page_identity_and_licensing_are_sealed(target_id):
    for field in ("page", "logical_page", "filename",
                  "logical_source_id", "source_role"):
        value = record(target_id)
        value["source_refs"][0][field] = "different"
        with pytest.raises(ValueError):
            assess_bigby_registered_other(value, target_id)


def test_two_rampolli_link_dedicated_statblock_page_without_replacing_narrative():
    for target_id in (
        "ref_b921e7e721755bbbac1b62bd6d70240b",
        "ref_1c9f8b60117d5649a6742b1de5e09b52",
    ):
        outcome = assess_bigby_registered_other(record(target_id), target_id)
        assert len(outcome["proposed_refs"]) == 2
        assert outcome["proposed_refs"][0]["page"] == TARGETS[target_id]["page"]
        assert outcome["proposed_refs"][1]["page"] == TARGETS[target_id]["stat_page"]


def test_wrong_dice_average_does_not_pass_global_gate():
    for target_id in TARGETS:
        attrs = dict(TARGETS[target_id]["attrs"])
        attrs["punti_ferita"] = attrs["punti_ferita"].replace(" + ", " + 1", 1)
        assert monster_semantic_numeric_flags(attrs)
