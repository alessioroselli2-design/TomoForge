"""Regression tests for read-only localized monster pilot gates."""
from copy import deepcopy

import pytest

from scripts.phase2_monster_dryrun import GateFailure, preview, preview_batch

SHA = "e" * 64


def reference():
    return {
        "id": "ref_a_test",
        "reference_type": "monster",
        "name": "Fictional Creature",
        "source_name": "Fictional Creature",
        "review_status": "verified",
        "translation_review_status": "pending",
        "description": "",
        "attributes": {
            "classe_armatura": "12", "punti_ferita": "19 (3d8 + 6)",
            "caratteristiche": {"for": 10},
        },
        "source_attributes": {
            "classe_armatura": "12", "punti_ferita": "19 (3d8 + 6)",
            "caratteristiche": {"for": 10},
        },
        "source_refs": [{
            "logical_source_id": "fake_2026_en",
            "physical_sha256": SHA, "page": 30,
        }],
    }


def candidate():
    return {
        "record_id": "ref_a_test",
        "name_en": "Fictional Creature",
        "name_it": "Creatura immaginaria",
        "name_basis": "licensed_it",
        "name_reference": "private:fictional-edition-italian-names",
        "name_collision_clear": True,
        "source_id": "fake_2026_en",
        "source_sha256": SHA, "source_page": 30,
        "translation_status": "draft",
        "translation_review_status": "pending",
        "description_it": (
            "Una creatura di fantasia impiegata per verificare il sistema."
        ),
        "source_has_actions_section": False,
        "expected_trait_count": 1, "expected_action_count": 0,
        "attributes_it": {
            "tratti": [{
                "nome": "Tratto fittizio",
                "descrizione": "Regola immaginaria per i soli test.",
            }],
            "azioni": [],
        },
    }


def test_italian_name_is_preserved_separately_and_no_data_is_changed():
    record, proposed = reference(), candidate()
    initial = deepcopy(record)
    result = preview_batch([record], [proposed])
    assert result["writes"] == 0
    assert result["passed"] == 1
    assert result["records"][0]["name_original"] == "Fictional Creature"
    assert result["records"][0]["name_italian"] == "Creatura immaginaria"
    assert result["records"][0]["translation_review_status"] == "pending"
    assert record == initial


def test_official_italian_name_may_match_original_proper_name():
    c = candidate()
    c.update({
        "name_it": "Fictional Creature",
        "name_basis": "official_it",
        "name_reference": "https://example.org/it-it/fictional-creature",
    })
    result = preview(reference(), c)
    assert result["name_italian"] == "Fictional Creature"


@pytest.mark.parametrize("field,value", [
    ("source_page", 29), ("source_sha256", "a" * 64),
    ("record_id", "other"), ("translation_review_status", "verified"),
    ("name_it", ""), ("name_basis", "guess"), ("name_reference", ""),
])
def test_rejects_invalid_identity_provenance_or_localization(field, value):
    c = candidate()
    c[field] = value
    with pytest.raises(GateFailure):
        preview(reference(), c)


def test_cannot_replace_existing_mechanical_core_field():
    c = candidate()
    c["attributes_it"]["punti_ferita"] = "99"
    with pytest.raises(GateFailure):
        preview(reference(), c)


def test_cannot_replace_previously_populated_traits():
    r = reference()
    r["attributes"]["tratti"] = [{
        "nome": "Originale", "descrizione": "Da conservare.",
    }]
    with pytest.raises(GateFailure):
        preview(r, candidate())


def test_cannot_invent_actions_without_an_original_actions_section():
    c = candidate()
    c["attributes_it"]["azioni"] = [{
        "nome": "Inventata", "descrizione": "Non risulta nella fonte.",
    }]
    c["expected_action_count"] = 1
    with pytest.raises(GateFailure):
        preview(reference(), c)


def test_missing_trait_blocks_the_candidate():
    c = candidate()
    c["expected_trait_count"] = 2
    with pytest.raises(GateFailure):
        preview(reference(), c)


def test_italian_name_collisions_block_entire_batch():
    other = reference()
    other["id"] = "ref_b_test"
    other["name"] = "Fictional Other"
    other["source_name"] = "Fictional Other"
    proposed = candidate()
    proposed["record_id"] = "ref_b_test"
    proposed["name_en"] = "Fictional Other"
    with pytest.raises(GateFailure):
        preview_batch([reference(), other], [candidate(), proposed])


def test_translated_names_require_collision_audit():
    c = candidate()
    c["name_collision_clear"] = False
    with pytest.raises(GateFailure):
        preview(reference(), c)
