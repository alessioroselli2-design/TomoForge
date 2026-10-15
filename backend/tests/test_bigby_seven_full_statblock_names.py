"""Fail-closed regressions for verified Bigby name-only corrections."""
from copy import deepcopy
import hashlib

import pytest

import services.bigby_seven_full_statblock_names as source
from services.bigby_seven_full_statblock_names import (
    SOURCE, TARGETS, source_locked_name_review,
)

SYNTHETIC = "This is synthetic raw data; no licensed PDF text is committed. " * 5


@pytest.fixture(params=list(TARGETS))
def sealed(request, monkeypatch):
    old = request.param
    id_, page, _new, checksum, _raw_hash = TARGETS[old]
    values = deepcopy(TARGETS)
    values[old] = (id_, page, _new, checksum,
                   hashlib.sha256(SYNTHETIC.encode("utf-8")).hexdigest())
    monkeypatch.setattr(source, "TARGETS", values)
    return old, {
        "id": id_, "user_id": "user_fabf28726a20",
        "name": old, "source_name": old,
        "normalized_name": old.casefold().replace("'", " "),
        "reference_type": "monster", "review_status": "verified",
        "review_flags": [], "canonical_id": None,
        "source_key": SOURCE, "source_language": "it",
        "source_text_checksum": checksum,
        "source_refs": [{
            "page": page, "logical_page": page, "ruleset": "2014",
            "filename": SOURCE, "source_role": "authority",
            "source_status": "active", "authority_class": "licensed_translation",
            "logical_source_id": "bgg_2023_it",
        }],
        "full_text": SYNTHETIC, "source_full_text": SYNTHETIC,
        "attributes": {
            "classe_armatura": "15",
            "punti_ferita": "22 (3d10 + 6)",
            "velocita": "12 m",
        },
    }


def test_exact_existing_record_is_eligible_and_unmodified(sealed):
    old, row = sealed
    before = deepcopy(row)
    verdict = source_locked_name_review(row, old)
    assert verdict["status"] == "eligible_verified_name_only_correction"
    assert verdict["writes"] == 0
    assert verdict["name_only"]
    assert verdict["source_title"].startswith("Gigante ")
    assert row == before


@pytest.mark.parametrize(("field", "invalid"), [
    ("id", "other"),
    ("user_id", "other"),
    ("name", "Other"),
    ("normalized_name", "wrong"),
    ("source_name", "wrong"),
    ("reference_type", "other"),
    ("review_status", "pending"),
    ("review_flags", ["ocr_da_verificare"]),
    ("canonical_id", "duplicate"),
    ("source_language", "en"),
    ("source_key", "wrong.pdf"),
    ("source_text_checksum", "0" * 64),
    ("full_text", "changed"),
    ("source_full_text", "changed"),
    ("source_refs", []),
    ("attributes", {}),
])
def test_wrong_record_or_source_fails_closed(sealed, field, invalid):
    old, row = sealed
    row[field] = invalid
    with pytest.raises(ValueError):
        source_locked_name_review(row, old)


@pytest.mark.parametrize(("field", "invalid"), [
    ("page", 999), ("logical_page", 999),
    ("filename", "else.pdf"), ("source_role", "secondary"),
    ("authority_class", "unlicensed"),
    ("logical_source_id", "other"),
])
def test_wrong_registered_page_fails_closed(sealed, field, invalid):
    old, row = sealed
    row["source_refs"][0][field] = invalid
    with pytest.raises(ValueError):
        source_locked_name_review(row, old)


def test_no_cross_record_name_lookup(sealed):
    _, row = sealed
    with pytest.raises(ValueError):
        source_locked_name_review(row, "Not a registered entity")
