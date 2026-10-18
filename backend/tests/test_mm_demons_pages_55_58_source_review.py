"""Source-specific fail-closed tests for MM demons on pages 55–58."""
from copy import deepcopy

import pytest

from services import mm_demons_pages_55_58_source_review as mod


def catalog():
    return {
        "logical_source_id": mod.SOURCE_ID,
        "physical_filename": mod.FILENAME,
        "physical_sha256": mod.SHA256,
        "physical_pages": mod.PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(
    ("name", "page", "hp", "gs"),
    [
        ("Balor", 55, "262 (21d12 + 126)", "19"),
        ("Barlgura", 56, "68 (8d10 + 24)", "5"),
        ("Chasme", 57, "84 (13d10 + 13)", "6"),
        ("Demone D'Ombra", 57, "66 (12d8 + 12)", "4"),
        ("Dretch", 58, "18 (4d6 + 4)", "1/4"),
        ("Glabrezu", 58, "157 (15d10 + 75)", "9"),
    ],
)
def test_all_original_separate_statblocks(name, page, hp, gs):
    result = mod.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == gs
    assert result["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert result["writes"] == 0


@pytest.mark.parametrize("name", list(mod.MONSTERS))
def test_duplicate_fails_closed(name):
    with pytest.raises(ValueError, match="already_present"):
        mod.audit(name, catalog(), record_exists=True)
    with pytest.raises(ValueError, match="already_present"):
        mod.audit(name, catalog(), same_name_monsters=[{"name": name}])


@pytest.mark.parametrize("field", [
    "logical_source_id", "physical_filename", "physical_sha256",
    "physical_pages", "source_status", "source_role", "authority_class",
])
def test_wrong_source_rejected(field):
    wrong = catalog()
    wrong[field] = "mismatched"
    with pytest.raises(ValueError, match="authority_drift"):
        mod.audit("Balor", wrong)


@pytest.mark.parametrize(
    ("name", "field", "wrong"),
    [
        ("Balor", "hp", "263 (21d12 + 127)"),
        ("Barlgura", "speed", "9 m, scalare 9 m"),
        ("Chasme", "ac", "16 (armatura naturale)"),
        ("Demone D'Ombra", "gs", "5"),
        ("Dretch", "kind", "Immondo Medio (demone)"),
        ("Glabrezu", "hp", "158 (15d10 + 76)"),
    ],
)
def test_source_metric_changed_fails(name, field, wrong, monkeypatch):
    altered = deepcopy(mod.MONSTERS)
    altered[name][field] = wrong
    monkeypatch.setattr(mod, "MONSTERS", altered)
    with pytest.raises(ValueError, match="sealed_source_fields"):
        mod.audit(name, catalog())


def test_two_distinct_boxes_on_pages_57_and_58():
    for page in (57, 58):
        records = [mod.audit(n, catalog()) for n, d in mod.MONSTERS.items() if d["page"] == page]
        assert len(records) == 2
        assert records[0]["id"] != records[1]["id"]


def test_no_shared_mutable_attributes():
    before = deepcopy(mod.MONSTERS["Balor"])
    copy = mod.audit("Balor", catalog())
    copy["attributes"]["caratteristiche"]["for"] = "1"
    assert mod.MONSTERS["Balor"] == before
