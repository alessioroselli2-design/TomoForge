"""Guard against swapped Eberron monster identities, OCR and adjacent blocks."""
from copy import deepcopy
import hashlib
import pytest
import services.eberron_four_reclass_review as review
from services.eberron_four_reclass_review import (
    SOURCE, USER_ID, SPECS, authority, assess_original_eberron_monster,
)
from services.ocr_semantic_gates import monster_semantic_numeric_flags

SYNTHETIC = "Eberron synthetic private-source description " * 12


@pytest.fixture(autouse=True)
def fixture_sha(monkeypatch):
    specs = deepcopy(SPECS)
    for spec in specs.values():
        spec["raw_hash"] = hashlib.sha256(SYNTHETIC.encode()).hexdigest()
    monkeypatch.setattr(review, "SPECS", specs)


def original(name):
    s = SPECS[name]
    return {
        "id": s["id"], "user_id": USER_ID, "name": name,
        "source_name": name, "normalized_name": name.casefold(),
        "reference_type": "other", "review_status": s["status"],
        "review_flags": [], "canonical_id": None,
        "source_language": "it", "source_key": SOURCE,
        "attributes": {}, "source_attributes": {},
        "review_corrections": deepcopy(s["corrections"]),
        "source_text_checksum": s["checksum"],
        "source_refs": [authority(s["page"])],
        "full_text": SYNTHETIC, "source_full_text": SYNTHETIC,
    }


@pytest.mark.parametrize("name", list(SPECS))
def test_each_source_stays_original_and_numeric_gate_passes(name):
    row = original(name)
    before = deepcopy(row)
    verdict = assess_original_eberron_monster(name, row)
    assert verdict["status"] == "eligible_original_source_reclassification"
    assert verdict["writes"] == 0
    assert row == before
    assert not monster_semantic_numeric_flags(verdict["proposed_attributes"])
    assert verdict["proposed_refs"][0]["page"] == SPECS[name]["page"]


@pytest.mark.parametrize("name", list(SPECS))
@pytest.mark.parametrize(("field", "bad"), [
    ("id", "wrong"), ("user_id", "other"), ("name", "other"),
    ("source_name", "other"), ("normalized_name", "wrong"),
    ("reference_type", "monster"), ("review_status", "pending"),
    ("review_flags", ["ocr_da_verificare"]), ("canonical_id", "collision"),
    ("source_language", "en"), ("source_key", "other.pdf"),
    ("source_text_checksum", "0"*64), ("attributes", {"classe_armatura":"10"}),
    ("source_attributes", {"punti_ferita":"1"}),
    ("review_corrections", {"changed":True}), ("source_refs", []),
    ("full_text", "changed"), ("source_full_text","changed"),
])
def test_any_record_drift_blocks_review(name, field, bad):
    row = original(name)
    row[field] = bad
    with pytest.raises(ValueError):
        assess_original_eberron_monster(name, row)


@pytest.mark.parametrize("name", list(SPECS))
def test_original_pdf_authority_and_duplicate_drift(name):
    row = original(name)
    row["source_refs"][0]["page"] = 1
    with pytest.raises(ValueError):
        assess_original_eberron_monster(name, row)
    row = original(name)
    row["source_refs"].append(authority(SPECS[name]["page"]))
    with pytest.raises(ValueError):
        assess_original_eberron_monster(name, row)


def test_sul_khatesh_separate_named_statblock_page():
    result = assess_original_eberron_monster("Sul Khatesh", original("Sul Khatesh"))
    assert [r["page"] for r in result["proposed_refs"]] == [314,315]


def test_hp_gate_cannot_be_bypassed():
    for name,spec in SPECS.items():
        attrs = dict(spec["attrs"])
        attrs["punti_ferita"] = "1 (10d10+1)"
        assert monster_semantic_numeric_flags(attrs), name
