"""Fail-closed statblock source tests for MM physical pages 140–143."""
from copy import deepcopy

import pytest
from services import mm_monsters_pages_140_143_source_review as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID,
        "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256,
        "physical_pages": mm.PDF_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(("name", "page", "hp", "gs"), [
    ("Fuoco Fatuo", 140, "22 (9d4)", "2"),
    ("Fustigatore", 141, "93 (11d10 + 33)", "5"),
    ("Galeb Duhr", 142, "85 (9d8 + 45)", "6"),
    ("Gargoyle", 143, "52 (7d8 + 21)", "2"),
])
def test_original_monster(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


def test_action_names_do_not_claim_full_transcription():
    record = mm.audit("Fustigatore", catalog())
    assert record["attributes"]["azioni_nomi_da_completare"] == [
        "Multiattacco", "Morso", "Tentacolo", "Riavvolgere",
    ]


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_duplicate_stops(name):
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), same_name_monsters=[{"name": name}])


def test_wrong_source_rejected():
    bad = catalog()
    bad["physical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="registered_source"):
        mm.audit("Gargoyle", bad)


@pytest.mark.parametrize(("name", "field", "wrong"), [
    ("Fuoco Fatuo", "hp", "23 (9d4)"),
    ("Fustigatore", "speed", "9 m"),
    ("Galeb Duhr", "gs", "5"),
    ("Gargoyle", "scores", [14, 11, 16, 6, 11, 7]),
    ("Fustigatore", "action_names", ["Morso"]),
])
def test_tampered_original_rejected(monkeypatch, name, field, wrong):
    changed = deepcopy(mm.MONSTERS)
    changed[name][field] = wrong
    monkeypatch.setattr(mm, "MONSTERS", changed)
    with pytest.raises(ValueError, match="source_fields_changed"):
        mm.audit(name, catalog())


def test_caller_cannot_change_source_proof():
    old = deepcopy(mm.MONSTERS["Gargoyle"])
    result = mm.audit("Gargoyle", catalog())
    result["attributes"]["caratteristiche"]["for"] = "30"
    result["attributes"]["azioni_nomi_da_completare"].append("Soffio")
    assert mm.MONSTERS["Gargoyle"] == old
