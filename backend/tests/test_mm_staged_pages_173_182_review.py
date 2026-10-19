"""Staging integrity tests (not canonical acceptance) for MM pages 173-182."""
from copy import deepcopy

import pytest

from services import mm_staged_pages_173_182_review as stage


def catalog():
    return {
        "logical_source_id": stage.SOURCE_ID,
        "physical_filename": stage.FILENAME,
        "physical_sha256": stage.SHA256,
        "physical_pages": stage.PAGE_COUNT,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(
    ("name", "page", "hp", "cr"),
    [["Grell",173,"55 (10d8 + 10)","3"],["Grick",174,"27 (6d8)","2"],["Grick Alfa",174,"75 (10d10 + 20)","7"],["Grifone",175,"59 (7d10 + 21)","2"],["Grimlock",176,"11 (2d8 + 2)","1/4"],["Guardiano Protettore",177,"142 (15d10 + 60)","7"],["Hobgoblin",179,"11 (2d8 + 2)","1/2"],["Hobgoblin Capitano",179,"39 (6d8 + 12)","3"],["Hobgoblin Signore Della Guerra",180,"97 (13d8 + 39)","6"],["Idra",181,"172 (15d12 + 75)","8"],["Ippogrifo",182,"19 (3d10 + 3)","1"]],
)
def test_all_staged_names_have_validated_core(name, page, hp, cr):
    result = stage.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == cr
    assert result["canonical_eligible"] is False
    assert result["status"] == "staged_pending_independent_visual_source_confirmation"
    assert result["writes"] == 0


def test_sibling_statblocks_have_different_ids():
    grick = stage.audit("Grick", catalog())
    alpha = stage.audit("Grick Alfa", catalog())
    assert grick["physical_page"] == alpha["physical_page"] == 174
    assert grick["id"] != alpha["id"]


def test_three_hobgoblin_variants_distinct():
    items = [
        stage.audit(n, catalog())
        for n in (
            "Hobgoblin",
            "Hobgoblin Capitano",
            "Hobgoblin Signore Della Guerra",
        )
    ]
    assert len({item["id"] for item in items}) == 3


@pytest.mark.parametrize("name", list(stage.INDEX))
def test_existing_monster_or_id_fails_closed(name):
    with pytest.raises(ValueError, match="monster_collision"):
        stage.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="monster_collision"):
        stage.audit(name, catalog(), same_name_monster=True)


def test_source_sha_mismatch_rejected():
    invalid = catalog()
    invalid["physical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="registered_original_source"):
        stage.audit("Idra", invalid)


def test_data_mutation_cannot_change_returned_core():
    a = stage.audit("Grell", catalog())
    a["attributes"]["caratteristiche"]["for"] = "30"
    b = stage.audit("Grell", catalog())
    assert b["attributes"]["caratteristiche"]["for"] == "15"


def test_stage_is_not_canonical_by_design():
    assert all(
        stage.audit(name, catalog())["canonical_eligible"] is False
        for name in stage.INDEX
    )


def test_integrity_gate_detects_modified_checksum(monkeypatch):
    copied = deepcopy(stage.INDEX)
    copied["Idra"]["source_text_checksum"] = "0" * 64
    monkeypatch.setattr(stage, "INDEX", copied)
    with pytest.raises(ValueError, match="checksum_drift"):
        stage.audit("Idra", catalog())
