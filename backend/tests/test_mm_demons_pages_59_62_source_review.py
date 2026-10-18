"""Fail-closed tests for demon boxed statblocks MM pages 59–62."""
from copy import deepcopy

import pytest

from services import mm_demons_pages_59_62_source_review as mm


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


@pytest.mark.parametrize(("name", "page", "hp", "gs"), [["Goristro",59,"310 (23d12 + 161)","17"],["Hezrou",60,"136 (13d10 + 65)","8"],["Mane",60,"9 (2d6 + 2)","1/8"],["Marilith",61,"189 (18d10 + 90)","16"],["Nalfeshnee",62,"184 (16d10 + 96)","13"]])
def test_exact_page_and_hp_core(name, page, hp, gs):
    r = mm.audit(name, catalog())
    assert r["physical_page"] == page
    assert r["attributes"]["punti_ferita"] == hp
    assert r["attributes"]["grado_sfida"] == gs
    assert r["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert r["writes"] == 0


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_duplicates_never_promoted(name):
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), duplicate_id=True)
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), duplicate_names=[{"name": name}])


def test_p60_two_independent_monsters():
    a = mm.audit("Hezrou", catalog())
    b = mm.audit("Mane", catalog())
    assert a["physical_page"] == b["physical_page"] == 60
    assert a["id"] != b["id"]


@pytest.mark.parametrize("field", ["physical_sha256", "source_status", "physical_pages"])
def test_registry_changed_fails(field):
    altered = catalog()
    altered[field] = "incorrect"
    with pytest.raises(ValueError, match="source_authority"):
        mm.audit("Goristro", altered)


@pytest.mark.parametrize(
    ("name", "field", "wrong"),
    [
        ("Goristro", "hp", "311 (23d12 + 162)"),
        ("Hezrou", "ac", "17 (armatura naturale)"),
        ("Mane", "gs", "1/4"),
        ("Marilith", "speed", "15 m"),
        ("Nalfeshnee", "hp", "185 (16d10 + 97)"),
    ],
)
def test_sealed_source_stat_drift(name, field, wrong, monkeypatch):
    new = deepcopy(mm.MONSTERS)
    new[name][field] = wrong
    monkeypatch.setattr(mm, "MONSTERS", new)
    with pytest.raises(ValueError, match="sealed_statblock"):
        mm.audit(name, catalog())
