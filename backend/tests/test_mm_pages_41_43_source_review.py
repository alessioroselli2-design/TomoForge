"""Source-confidence gates for Chuul, Ciclope and two distinct Coboldi."""
from copy import deepcopy

import pytest

from services import mm_pages_41_43_source_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA,
        "physical_pages": mm.PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(
    ("name", "page", "ca", "hp", "gs"),
    [
        ("Chuul", 41, "16 (armatura naturale)", "93 (11d10 + 33)", "4"),
        ("Ciclope", 42, "14 (armatura naturale)", "138 (12d12 + 60)", "6"),
        ("Coboldo Alato", 43, "13", "7 (3d6 - 3)", "1/4"),
        ("Coboldo", 43, "12", "5 (2d6 - 2)", "1/8"),
    ],
)
def test_original_boxed_statblocks(name, page, ca, hp, gs):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["classe_armatura"] == ca
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == gs
    assert result["writes"] == 0


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_any_existing_monster_collision_fails_closed(name):
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), existing_monster_names=[{"name": name}])


def test_coboldo_lore_is_not_the_monster_statblock():
    assert mm.MONSTERS["Coboldo Alato"]["id"] != mm.MONSTERS["Coboldo"]["id"]
    a = mm.audit("Coboldo", catalog())
    b = mm.audit("Coboldo Alato", catalog())
    assert a["attributes"]["punti_ferita"] != b["attributes"]["punti_ferita"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("physical_sha256", "f" * 64),
        ("physical_filename", "wrong.pdf"),
        ("physical_pages", 152),
        ("source_status", "duplicate"),
    ],
)
def test_registered_manual_mismatch_fails(field, value):
    bad = catalog()
    bad[field] = value
    with pytest.raises(ValueError, match="registered_source"):
        mm.audit("Chuul", bad)


@pytest.mark.parametrize(
    ("name", "key", "value"),
    [
        ("Coboldo", "hp", "5 (2d6 + 2)"),
        ("Coboldo Alato", "hp", "7 (3d6 + 3)"),
        ("Chuul", "ac", "17 (armatura naturale)"),
        ("Ciclope", "gs", "5"),
    ],
)
def test_changed_plausible_statistics_fail_source_seal(name, key, value, monkeypatch):
    copied = deepcopy(mm.MONSTERS)
    copied[name][key] = value
    monkeypatch.setattr(mm, "MONSTERS", copied)
    with pytest.raises(ValueError, match="source_fields_unsealed"):
        mm.audit(name, catalog())


def test_mutating_result_cannot_alter_sealed_source():
    before = deepcopy(mm.MONSTERS["Coboldo"])
    output = mm.audit("Coboldo", catalog())
    output["attributes"]["caratteristiche"]["for"] = "30"
    assert mm.MONSTERS["Coboldo"] == before
