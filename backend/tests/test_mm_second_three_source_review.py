"""Original-source gates for Ankheg, Arpia, Artiglio Strisciante."""

from copy import deepcopy

import pytest

from services import mm_second_three_source_review as m


def authority():
    return {
        "logical_source_id": m.SOURCE_ID,
        "physical_filename": m.MANUAL,
        "physical_sha256": m.SHA256,
        "physical_pages": m.EXPECTED_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(
    ("name", "page", "ac", "hp", "speed", "gs"),
    [
        ("Ankheg", 19, "14 (armatura naturale), 11 se prono",
         "39 (6d10 + 6)", "9 m, scavare 3 m", "2"),
        ("Arpia", 20, "11", "38 (7d8 + 7)", "6 m, volare 12 m", "1"),
        ("Artiglio Strisciante", 21, "12", "2 (1d4)", "6 m, scalare 6 m", "0"),
    ],
)
def test_three_named_visual_statblocks(name, page, ac, hp, speed, gs):
    result = m.audit_mm_second_batch(name, None, [], authority())
    assert result["physical_page"] == page
    assert result["attributes"]["classe_armatura"] == ac
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["velocita"] == speed
    assert result["attributes"]["grado_sfida"] == gs
    assert result["ocr_is_not_auto_verified"] is True
    assert result["writes"] == 0


@pytest.mark.parametrize("name", list(m.MONSTERS))
def test_duplicate_fails_closed(name):
    with pytest.raises(ValueError, match="duplicate"):
        m.audit_mm_second_batch(name, {"id": m.MONSTERS[name]["id"]}, [], authority())
    with pytest.raises(ValueError, match="duplicate"):
        m.audit_mm_second_batch(name, None, [{"name": name}], authority())


@pytest.mark.parametrize("field", [
    "physical_filename", "physical_sha256", "physical_pages",
    "source_status", "source_role", "authority_class",
])
def test_authority_mismatch_fails(field):
    source = authority()
    source[field] = "wrong"
    with pytest.raises(ValueError, match="authority"):
        m.audit_mm_second_batch("Ankheg", None, [], source)


@pytest.mark.parametrize("name,key,value", [
    ("Ankheg", "ac", "15 (armatura naturale), 11 se prono"),
    ("Ankheg", "hp", "40 (6d10 + 7)"),
    ("Arpia", "speed", "6 m, volare 15 m"),
    ("Arpia", "challenge", "2"),
    ("Artiglio Strisciante", "kind", "Umanoide Minuscolo"),
    ("Artiglio Strisciante", "hp", "3 (1d4)"),
])
def test_changed_but_plausible_facts_cannot_pass(name, key, value, monkeypatch):
    changed = deepcopy(m.MONSTERS)
    changed[name][key] = value
    monkeypatch.setattr(m, "MONSTERS", changed)
    with pytest.raises(ValueError, match="sealed"):
        m.audit_mm_second_batch(name, None, [], authority())


def test_hit_dice_without_modifier_is_still_checked():
    result = m.audit_mm_second_batch("Artiglio Strisciante", None, [], authority())
    assert result["attributes"]["punti_ferita"] == "2 (1d4)"


def test_returned_attributes_do_not_mutate_sealed_source():
    before = deepcopy(m.MONSTERS["Arpia"])
    result = m.audit_mm_second_batch("Arpia", None, [], authority())
    result["attributes"]["caratteristiche"]["for"] = "1"
    assert m.MONSTERS["Arpia"] == before
