"""Source-lock tests for three independently boxed MPMM creature records."""
from copy import deepcopy
import hashlib
import pytest

import services.mpmm_three_other_verified_source_review as audit
from services.mpmm_three_other_verified_source_review import (
    OWNER, SOURCE, TARGETS, authority, review_existing_creature,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE = "Synthetic noncopyrighted test record text. " * 7


@pytest.fixture(params=list(TARGETS))
def original(request, monkeypatch):
    name = request.param
    spec = TARGETS[name]
    altered = deepcopy(TARGETS)
    altered[name]["raw_sha"] = hashlib.sha256(FAKE.encode()).hexdigest()
    monkeypatch.setattr(audit, "TARGETS", altered)
    return name, {
        "id": spec["id"], "user_id": OWNER,
        "name": name, "source_name": name, "normalized_name": name.casefold(),
        "reference_type": "other", "review_status": "verified",
        "review_flags": [], "canonical_id": None, "source_key": SOURCE,
        "source_language": "it", "source_text_checksum": spec["checksum"],
        "source_refs": [authority(spec["page"])], "attributes": {},
        "source_attributes": {}, "review_corrections": {},
        "full_text": FAKE, "source_full_text": FAKE,
    }


def test_valid_original_not_mutated(original):
    name, row = original
    before = deepcopy(row)
    outcome = review_existing_creature(name, row)
    assert outcome["status"] == "eligible_original_creature_reclassification"
    assert outcome["historically_verified_as_other_only"]
    assert outcome["writes"] == 0
    assert row == before
    assert not monster_semantic_numeric_flags(outcome["attributes"])


@pytest.mark.parametrize(("field", "bad"), [
    ("id", "other"), ("user_id", "wrong"),
    ("name", "wrong"), ("source_name", "wrong"),
    ("normalized_name", "wrong"), ("reference_type", "monster"),
    ("review_status", "needs_review"), ("review_flags", ["ocr_da_verificare"]),
    ("canonical_id", "duplicate"), ("source_key", "wrong.pdf"),
    ("source_language", "en"), ("source_text_checksum", "0"*64),
    ("source_refs", []), ("attributes", {"classe_armatura": "16"}),
    ("source_attributes", {"punti_ferita": "90"}),
    ("review_corrections", {"_source_changed": True}),
    ("full_text", "changed"), ("source_full_text", "changed"),
])
def test_drift_blocks(original, field, bad):
    name, row = original
    row[field] = bad
    with pytest.raises(ValueError):
        review_existing_creature(name, row)


@pytest.mark.parametrize(("field", "bad"), [
    ("page", 1), ("logical_page", 201), ("filename", "wrong.pdf"),
    ("source_role", "secondary"), ("source_status", "inactive"),
    ("authority_class", "unlicensed"), ("logical_source_id", "other"),
])
def test_wrong_original_page_blocks(original, field, bad):
    name, row = original
    row["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        review_existing_creature(name, row)


def test_duplicate_authority_rejected(original):
    name, row = original
    row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        review_existing_creature(name, row)


def test_math_gate_rejects_bad_hp():
    for spec in TARGETS.values():
        hp, count, faces, bonus = spec["dice"]
        assert (count*(faces+1))//2+bonus == hp
        wrong = dict(spec["attrs"])
        wrong["punti_ferita"] = f"{hp} ({count}d{faces} + {bonus + 1})"
        assert monster_semantic_numeric_flags(wrong)
