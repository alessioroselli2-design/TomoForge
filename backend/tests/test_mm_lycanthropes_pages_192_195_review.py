"""Fail-closed lycanthrope source gates, forms and HP arithmetic."""
from copy import deepcopy

import pytest

from services import mm_lycanthropes_pages_192_195_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256,
        "physical_pages": mm.PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(("name","page","hp","cr"), [["Cinghiale Mannaro",192,"78 (12d8 + 24)","4"],["Orso Mannaro",193,"135 (18d8 + 54)","5"],["Lupo Mannaro",193,"58 (9d8 + 18)","3"],["Tigre Mannara",194,"120 (16d8 + 48)","4"],["Topo Mannaro",195,"33 (6d8 + 6)","2"]])
def test_source_boxes(name, page, hp, cr):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == cr
    assert result["writes"] == 0


def test_two_separate_original_boxes_on_p193():
    bear = mm.audit("Orso Mannaro", catalog())
    wolf = mm.audit("Lupo Mannaro", catalog())
    assert bear["physical_page"] == wolf["physical_page"] == 193
    assert bear["id"] != wolf["id"]


def test_form_dependent_armor_and_speed_preserved():
    boar = mm.audit("Cinghiale Mannaro", catalog())
    assert "11 (armatura naturale)" in boar["attributes"]["classe_armatura"]
    assert "12 m in forma di cinghiale" in boar["attributes"]["velocita"]


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_duplicate_never_passes(name):
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        mm.audit(name, catalog(), same_named_monster=True)


def test_wrong_manual_hash_rejected():
    c = catalog()
    c["physical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.audit("Lupo Mannaro", c)


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_tampered_source_fields_rejected(monkeypatch, name):
    changed = deepcopy(mm.MONSTERS)
    changed[name]["gs"] = "20"
    monkeypatch.setattr(mm, "MONSTERS", changed)
    with pytest.raises(ValueError, match="original_source_fields_changed"):
        mm.audit(name, catalog())


def test_return_mutation_does_not_change_source():
    record = mm.audit("Tigre Mannara", catalog())
    record["attributes"]["caratteristiche"]["for"] = "30"
    record2 = mm.audit("Tigre Mannara", catalog())
    assert record2["attributes"]["caratteristiche"]["for"] == "17"
