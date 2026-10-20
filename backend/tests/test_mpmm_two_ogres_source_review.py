"""Fail-closed negative regressions for the two MPMM Ogre boxed statblocks."""
from copy import deepcopy
import hashlib
import pytest

import services.mpmm_two_ogres_source_review as audit
from services.mpmm_two_ogres_source_review import (
    TARGETS, SOURCE, OWNER, authority, inspect_ogre,
)

SYNTHETIC = "Synthetic test narrative without copyrighted publisher text. " * 5


@pytest.fixture(params=list(TARGETS))
def original(request, monkeypatch):
    name = request.param
    t = TARGETS[name]
    clone = deepcopy(TARGETS)
    clone[name]["raw_sha"] = hashlib.sha256(SYNTHETIC.encode()).hexdigest()
    monkeypatch.setattr(audit, "TARGETS", clone)
    row = {
        "id": t["id"], "user_id": OWNER,
        "name": t["original_name"],
        "normalized_name": t["original_name"].casefold(),
        "source_name": t["original_name"],
        "reference_type": "other", "review_status": "needs_review",
        "review_flags": t["flags"], "canonical_id": None,
        "source_key": SOURCE, "source_language": "it",
        "source_text_checksum": t["checksum"],
        "source_refs": [authority()],
        "review_corrections": {"_source_changed": True},
        "attributes": {}, "source_attributes": {},
        "full_text": SYNTHETIC, "source_full_text": SYNTHETIC,
    }
    return name, row


def test_originals_are_read_only_eligible(original):
    name, row = original
    snapshot = deepcopy(row)
    verdict = inspect_ogre(name, row)
    assert verdict["status"] == "eligible_existing_ogre_monster_reclassification"
    assert verdict["correct_name"] == name
    assert verdict["writes"] == 0
    assert row == snapshot


@pytest.mark.parametrize(("field", "bad"), [
    ("id", "different"), ("user_id", "wrong"),
    ("name", "Different"), ("normalized_name", "wrong"),
    ("source_name", "Ogre Bunker"), ("reference_type", "monster"),
    ("review_status", "verified"), ("review_flags", ["another"]),
    ("canonical_id", "duplicate"), ("source_key", "different.pdf"),
    ("source_language", "en"), ("source_text_checksum", "0"*64),
    ("attributes", {"classe_armatura":"11"}), ("source_attributes", {"velocita":"12 m"}),
    ("review_corrections", {}), ("source_refs", []),
    ("full_text", "changed"), ("source_full_text", "changed"),
])
def test_any_original_source_change_blocks(original, field, bad):
    name, row = original
    row[field] = bad
    with pytest.raises(ValueError):
        inspect_ogre(name, row)


@pytest.mark.parametrize(("field", "bad"), [
    ("page", 8), ("logical_page", 208), ("filename", "other.pdf"),
    ("logical_source_id", "erlw_2019_it"), ("source_role", "secondary"),
    ("authority_class", "unlicensed"), ("ruleset", "2024"),
])
def test_wrong_original_page_or_authority_blocks(original, field, bad):
    name, row = original
    row["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        inspect_ogre(name, row)


def test_same_source_page_is_not_a_duplicate(original):
    name, row = original
    result = inspect_ogre(name, row)
    assert result["source_page"] == 207
    with pytest.raises(ValueError):
        inspect_ogre("Ogre Di Guerra", row)
