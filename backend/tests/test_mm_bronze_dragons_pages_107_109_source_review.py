"""Fail-closed gates for original Italian MM bronze dragons p107–109."""
from copy import deepcopy

import pytest

from services import mm_bronze_dragons_pages_107_109_source_review as mm


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


@pytest.mark.parametrize(("name", "page", "hp", "gs"), [["Drago Di Bronzo Antico",107,"444 (24d20 + 192)","22"],["Drago Di Bronzo Adulto",108,"212 (17d12 + 102)","15"],["Drago Di Bronzo Giovane",108,"142 (15d10 + 60)","8"],["Drago Di Bronzo Cucciolo",109,"32 (5d8 + 10)","2"]])
def test_original_bronze_age_block(name, page, hp, gs):
    result = mm.audit(name, catalog())
    assert result["physical_page"] == page
    assert result["attributes"]["punti_ferita"] == hp
    assert result["attributes"]["grado_sfida"] == gs
    assert result["writes"] == 0


def test_two_independent_p108_monsters():
    adult = mm.audit("Drago Di Bronzo Adulto", catalog())
    young = mm.audit("Drago Di Bronzo Giovane", catalog())
    assert adult["physical_page"] == young["physical_page"] == 108
    assert adult["id"] != young["id"]


@pytest.mark.parametrize("name", list(mm.MONSTERS))
def test_duplicate_fails_closed(name):
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), existing_id=True)
    with pytest.raises(ValueError, match="duplicate"):
        mm.audit(name, catalog(), monster_name_matches=[{"name": name}])


def test_source_authority_mismatch():
    wrong = catalog()
    wrong["physical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source_mismatch"):
        mm.audit("Drago Di Bronzo Antico", wrong)


@pytest.mark.parametrize(
    ("name", "key", "value"),
    [
        ("Drago Di Bronzo Antico", "hp", "445 (24d20 + 193)"),
        ("Drago Di Bronzo Adulto", "gs", "16"),
        ("Drago Di Bronzo Giovane", "size", "Enorme"),
        ("Drago Di Bronzo Cucciolo", "speed", "12 m"),
    ],
)
def test_modified_source_fields_rejected(name, key, value, monkeypatch):
    tampered = deepcopy(mm.MONSTERS)
    tampered[name][key] = value
    monkeypatch.setattr(mm, "MONSTERS", tampered)
    with pytest.raises(ValueError):
        mm.audit(name, catalog())
