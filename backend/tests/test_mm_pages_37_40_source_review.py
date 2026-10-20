"""Fail-closed original source checks: Italian Monster Manual pages 37–40."""
from copy import deepcopy

import pytest

from services import mm_pages_37_40_source_review as review


def catalog():
    return {
        "logical_source_id": review.SOURCE_ID,
        "physical_filename": review.FILENAME,
        "physical_sha256": review.PHYSICAL_SHA256,
        "physical_pages": review.PAGE_COUNT,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(
    ("name", "page", "ac", "hp", "gs"),
    [
        ("Cavaliere Della Morte", 37, "20 (armatura completa, scudo)", "180 (19d8 + 95)", "17"),
        ("Cavallo Degli Incubi", 38, "13 (armatura naturale)", "68 (8d10 + 24)", "3"),
        ("Centauro", 39, "12", "45 (6d10 + 12)", "2"),
        ("Chimera", 40, "14 (armatura naturale)", "114 (12d10 + 48)", "6"),
    ],
)
def test_visual_statblock_is_source_sealed(name, page, ac, hp, gs):
    result = review.audit_mm_page_37_40(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["classe_armatura"] == ac
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == gs
    assert result["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert result["writes"] == 0


@pytest.mark.parametrize("name", list(review.MONSTERS))
def test_monster_duplicates_fail_closed(name):
    with pytest.raises(ValueError, match="already_present"):
        review.audit_mm_page_37_40(name, catalog(), monster_id_collision=True)
    with pytest.raises(ValueError, match="already_present"):
        review.audit_mm_page_37_40(name, catalog(), monster_name_collisions=[{"name": name}])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("physical_sha256", "0" * 64),
        ("physical_filename", "Manuale del Giocatore.pdf"),
        ("physical_pages", 321),
        ("source_status", "duplicate"),
        ("source_role", "extraction_aid"),
        ("authority_class", "unlicensed"),
        ("text_mode", "text"),
    ],
)
def test_invalid_original_catalog_is_rejected(field, value):
    wrong = catalog()
    wrong[field] = value
    with pytest.raises(ValueError, match="original_source"):
        review.audit_mm_page_37_40("Chimera", wrong)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ac", "21 (armatura completa, scudo)"),
        ("hp", "181 (19d8 + 96)"),
        ("speed", "12 m"),
        ("gs", "18"),
        ("kind", "Non morto Grande"),
    ],
)
def test_plausible_changed_fields_never_pass(field, value, monkeypatch):
    new = deepcopy(review.MONSTERS)
    new["Cavaliere Della Morte"][field] = value
    monkeypatch.setattr(review, "MONSTERS", new)
    with pytest.raises(ValueError, match="sealed_source"):
        review.audit_mm_page_37_40("Cavaliere Della Morte", catalog())


def test_nonmonster_lore_record_is_not_false_collision():
    result = review.audit_mm_page_37_40("Centauro", catalog(), monster_name_collisions=[])
    assert result["name"] == "Centauro"


def test_mutating_returned_attributes_does_not_change_audit():
    before = deepcopy(review.MONSTERS["Centauro"])
    result = review.audit_mm_page_37_40("Centauro", catalog())
    result["attributes"]["caratteristiche"]["for"] = "1"
    assert review.MONSTERS["Centauro"] == before
