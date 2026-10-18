"""Gated source proofs for the Italian MM Cockatrice and Couatl."""
from copy import deepcopy

import pytest

from services import mm_pages_44_45_source_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256,
        "physical_pages": mm.PHYSICAL_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(
    ("name", "page", "ca", "hp", "gs"),
    [
        ("Cockatrice", 44, "11", "27 (6d6 + 6)", "1/2"),
        ("Couatl", 45, "19 (armatura naturale)", "97 (13d8 + 39)", "4"),
    ],
)
def test_exact_source_proof(name, page, ca, hp, gs):
    row = mm.audit(name, catalog())
    assert row["physical_page"] == page
    assert row["attributes"]["classe_armatura"] == ca
    assert row["attributes"]["punti_ferita"] == hp
    assert row["attributes"]["grado_sfida"] == gs
    assert row["status"] == "eligible_original_source_core_statblock"
    assert row["writes"] == 0


@pytest.mark.parametrize("name", ["Cockatrice", "Couatl"])
def test_duplicate_monster_fails_closed(name):
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), id_collision=True)
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), monster_name_collisions=[{"name": name}])


@pytest.mark.parametrize("field", [
    "logical_source_id", "physical_filename", "physical_sha256",
    "physical_pages", "source_status", "authority_class",
])
def test_source_catalog_mismatch_is_a_hard_error(field):
    source = catalog()
    source[field] = "invalid"
    with pytest.raises(ValueError, match="source_authority"):
        mm.audit("Couatl", source)


@pytest.mark.parametrize(
    ("name", "field", "wrong"),
    [
        ("Cockatrice", "ac", "12"),
        ("Cockatrice", "hp", "28 (6d6 + 7)"),
        ("Couatl", "gs", "5"),
        ("Couatl", "kind", "Aberrazione Media"),
    ],
)
def test_changed_plausible_values_cannot_pass(name, field, wrong, monkeypatch):
    copied = deepcopy(mm.MONSTERS)
    copied[name][field] = wrong
    monkeypatch.setattr(mm, "MONSTERS", copied)
    with pytest.raises(ValueError, match="original_statblock_fields_modified"):
        mm.audit(name, catalog())


def test_result_is_isolated_from_sealed_source():
    before = deepcopy(mm.MONSTERS["Couatl"])
    result = mm.audit("Couatl", catalog())
    result["attributes"]["caratteristiche"]["for"] = "1"
    assert mm.MONSTERS["Couatl"] == before
