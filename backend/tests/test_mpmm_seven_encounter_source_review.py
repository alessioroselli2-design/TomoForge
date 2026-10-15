"""Source-correct, no-write and negative tests for seven MPMM encounter creatures."""
import hashlib
from copy import deepcopy
import pytest

import services.mpmm_seven_encounter_source_review as mod
from services.mpmm_seven_encounter_source_review import (
    OWNER, TARGETS, original_refs, review_existing_statblock,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE_RAW = "Synthetic original description without licensed publisher prose. " * 5


@pytest.fixture(params=list(TARGETS))
def registered(request, monkeypatch):
    name = request.param
    t = TARGETS[name]
    specs = deepcopy(TARGETS)
    specs[name]["raw"] = hashlib.sha256(FAKE_RAW.encode()).hexdigest()
    monkeypatch.setattr(mod, "TARGETS", specs)
    return name, {
        "id": t["id"], "user_id": OWNER,
        "name": name, "source_name": name, "normalized_name": name.casefold(),
        "reference_type": "other", "review_status": "needs_review",
        "review_flags": [], "canonical_id": None, "source_language": "it",
        "source_key": t["source"], "source_text_checksum": t["checksum"],
        "review_corrections": {"_source_changed": True},
        "attributes": {}, "source_attributes": {},
        "source_refs": original_refs(t["source"], t["pages"]),
        "full_text": FAKE_RAW, "source_full_text": FAKE_RAW,
    }


def test_guarded_source_and_math_eligible_readonly(registered):
    name, row = registered
    before = deepcopy(row)
    result = review_existing_statblock(name, row)
    assert result["eligible"]
    assert result["writes"] == 0
    assert result["attributes"] == TARGETS[name]["attrs"]
    assert row == before
    assert not monster_semantic_numeric_flags(result["attributes"])


@pytest.mark.parametrize(("field", "bad"), [
    ("id","wrong"), ("name","wrong"),
    ("source_name","wrong"), ("normalized_name","wrong"),
    ("user_id","wrong"), ("reference_type","monster"),
    ("review_status","verified"), ("review_flags",["ocr_da_verificare"]),
    ("canonical_id","collision"), ("source_language","en"),
    ("source_key","wrong.pdf"), ("source_text_checksum","0"*64),
    ("source_refs",[]), ("attributes",{"classe_armatura":"13"}),
    ("source_attributes",{"punti_ferita":"5"}),
    ("review_corrections",{}), ("full_text","wrong"),
    ("source_full_text","wrong"),
])
def test_mutation_fail_closed(registered, field, bad):
    name, row = registered
    row[field] = bad
    with pytest.raises(ValueError):
        review_existing_statblock(name, row)


@pytest.mark.parametrize(("field", "bad"), [
    ("page", 1), ("logical_page", 400), ("filename","wrong.pdf"),
    ("source_role","secondary"), ("source_status","inactive"),
    ("authority_class","unlicensed"), ("logical_source_id","not_mpmm"),
    ("ruleset","2024"),
])
def test_original_authority_provenance_strict(registered, field, bad):
    name, row = registered
    row["source_refs"][0][field] = bad
    with pytest.raises(ValueError):
        review_existing_statblock(name, row)


def test_duplicate_page_or_incorrect_creature_fails(registered):
    name, row = registered
    row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        review_existing_statblock(name, row)
    with pytest.raises(ValueError):
        review_existing_statblock("Nonexisting other creature", row)


def test_named_githyanki_has_two_exact_source_pages():
    assert TARGETS["Githyanki Gish"]["pages"] == [35, 36]


def test_dice_arithmetic_matches_without_weakened_gate():
    for t in TARGETS.values():
        hp, count, sides, bonus = t["dice"]
        assert count*(sides+1)//2+bonus == hp
        damaged = {**t["attrs"], "punti_ferita": f"{hp} ({count}d{sides} + {bonus+1})"}
        assert monster_semantic_numeric_flags(damaged)
