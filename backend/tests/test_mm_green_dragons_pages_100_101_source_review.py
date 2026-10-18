"""Fail-closed source and semantic gates: green dragon age categories."""
from copy import deepcopy

import pytest

from services import mm_green_dragons_pages_100_101_source_review as mm


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
    ("name", "page", "hp", "gs"),
    [["Drago Verde Antico",100,"385 (22d20 + 154)","22"],["Drago Verde Adulto",101,"207 (18d12 + 90)","15"],["Drago Verde Giovane",101,"136 (16d10 + 48)","8"],["Drago Verde Cucciolo",101,"38 (7d8 + 7)","2"]],
)
def test_source_exact_age_block(name, page, hp, gs):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == gs
    assert result["attributes"]["completezza_scheda"] == "statistiche_essenziali"
    assert result["writes"] == 0


def test_three_independent_p101_boxes():
    names = ("Drago Verde Adulto", "Drago Verde Giovane", "Drago Verde Cucciolo")
    rows = [mm.audit(name, catalog()) for name in names]
    assert all(row["physical_page"] == 101 for row in rows)
    assert len({row["id"] for row in rows}) == 3


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_duplicate_fails_closed(name):
    with pytest.raises(ValueError, match="duplicate_detected"):
        mm.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="duplicate_detected"):
        mm.audit(name, catalog(), monster_name_matches=[{"name": name}])


def test_uncatalogued_pdf_is_rejected():
    bad = catalog()
    bad["physical_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="source_mismatch"):
        mm.audit("Drago Verde Antico", bad)


@pytest.mark.parametrize(
    ("name", "field", "wrong"),
    [
        ("Drago Verde Antico", "hp", "386 (22d20 + 155)"),
        ("Drago Verde Adulto", "gs", "16"),
        ("Drago Verde Giovane", "size", "Enorme"),
        ("Drago Verde Cucciolo", "speed", "12 m"),
    ],
)
def test_source_modified_values_fail(monkeypatch, name, field, wrong):
    tampered = deepcopy(mm.MONSTERS)
    tampered[name][field] = wrong
    monkeypatch.setattr(mm, "MONSTERS", tampered)
    with pytest.raises(ValueError):
        mm.audit(name, catalog())
