"""Fail-closed source-locked census of Kwalish appendix monster statblocks."""
import json
import math
import re
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "llok_2018_en_source_review_core.json"
SHA = "3afc9e88420a930666f6995834ae06a3e3dc587cb8a3b437aa15c9adb8423602"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
ABILITIES = {"for", "des", "cos", "int", "sag", "car"}


def test_authority_and_scope_are_locked():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "llok_2018_en"
    assert d["authority"]["sha256"] == SHA
    assert d["authority"]["physical_pdf_pages"] == 62
    assert d["audit"]["total_statblocks"] == 38
    assert d["audit"]["new_candidates"] == 6
    assert d["audit"]["existing_identities"] == 32
    assert d["audit"]["database_writes"] == 0
    assert not d["audit"]["integral_actions_traits_spells_complete"]
    assert not d["audit"]["original_pdf_or_raw_ocr_committed"]


def test_all_38_core_fields_match_source_math():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    rows = d["statblocks"]
    assert len(rows) == 38
    assert len({r["name"].casefold() for r in rows}) == 38
    for x in rows:
        assert 38 <= x["physical_pdf_page"] <= 53
        assert x["completeness"] == "statistiche_essenziali"
        assert x["source_review"] == "original_pdf_text_and_visual"
        assert x["armor_class"] and x["speed"]
        assert set(x["ability_scores"]) == ABILITIES
        assert all(isinstance(v, int) and 1 <= v <= 30 for v in x["ability_scores"].values())
        assert re.fullmatch(r"(?:0|[1-9]\d*)(?:/[1-9]\d*)?", x["challenge_rating"])
        match = DICE.fullmatch(x["hit_points"])
        assert match, x["name"]
        hp, count, sides, sign, modifier = match.groups()
        mean = math.floor(int(count) * (int(sides) + 1) / 2)
        mean += int(modifier or 0) * (-1 if sign == "-" else 1)
        assert int(hp) == mean, x["name"]


def test_new_and_existing_aliases_do_not_collide():
    rows = json.loads(PATH.read_text(encoding="utf-8"))["statblocks"]
    new = [r for r in rows if r["import_decision"] == "candidate_new"]
    linked = [r for r in rows if r["import_decision"] == "link_existing_identity"]
    assert len(new) == 6
    assert len(linked) == 32
    assert all(r["existing_canonical_name"] is None for r in new)
    assert all(r["existing_canonical_name"] for r in linked)
    assert {r["name"] for r in new} == {
        "Clockwork Kraken", "Froghemoth", "Garret Levistusson",
        "Mary Greymalkin", "Mind Flayer Arcanist", "Ooze-Folk",
    }


def test_source_specific_version_conflicts_preserved():
    records = {
        r["name"]: r
        for r in json.loads(PATH.read_text(encoding="utf-8"))["statblocks"]
    }
    assert records["Brain in a Jar"]["existing_canonical_name"] == "Cervello in Barattolo"
    assert records["Brain in a Jar"]["cross_source_variant"]
    assert records["Brain in a Jar"]["hit_points"] == "58 (9d8 + 18)"
    assert records["Evoker"]["existing_canonical_name"] == "Mago Invocatore"
    assert records["Evoker"]["hit_points"] == "66 (12d8 + 12)"
    assert records["Evoker"]["cross_source_variant"]
