"""Source-locked census for 5 original The Tortle Package statblocks."""
import json
import math
import re
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "tortle_2017_en_core_visual_review.json"
SHA = "3dea9cd685343b1d90207b2b79f4a963cb3131f30e67f23d10795ace8f9f1a44"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
SIX = {"for", "des", "cos", "int", "sag", "car"}


def test_source_and_decisions():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    assert d["authority"]["sha256"] == SHA
    assert d["authority"]["physical_pdf_pages"] == 28
    assert d["authority"]["logical_source_id"] == "tortle_2017_en"
    assert d["audit"]["database_writes"] == 0
    assert d["audit"]["statblocks_with_six_scores"] == 5
    assert d["audit"]["new_candidates"] == 3
    assert d["audit"]["existing_translated_aliases"] == 2
    assert d["audit"]["actions_traits_spells_complete"] is False
    assert d["audit"]["source_private_pdf_not_committed"]
    assert "Marine Decapus" in d["audit"]["marine_decapus_note"]


def test_all_statblock_cores_and_dice():
    rows = json.loads(PATH.read_text(encoding="utf-8"))["statblocks"]
    assert len(rows) == 5
    assert len({x["name"].lower() for x in rows}) == 5
    for row in rows:
        assert 21 <= row["physical_pdf_page"] <= 23
        assert row["source_review"] == "original_pdf_page_visual"
        assert row["completeness"] == "statistiche_essenziali"
        assert row["armor_class"] > 0 and row["speed"]
        assert set(row["ability_scores"]) == SIX
        assert all(1 <= n <= 30 for n in row["ability_scores"].values())
        assert re.fullmatch(r"(?:0|[1-9]\d*)(?:/[1-9]\d*)?", row["challenge_rating"])
        m = DICE.fullmatch(row["hit_points"])
        assert m, row["name"]
        avg, ndice, die, sign, bonus = m.groups()
        expected = math.floor(int(ndice) * (int(die) + 1) / 2)
        expected += int(bonus or 0) * (-1 if sign == "-" else 1)
        assert int(avg) == expected, row["name"]


def test_reuse_existing_italian_identities():
    rows = json.loads(PATH.read_text(encoding="utf-8"))["statblocks"]
    aliases = {r["name"]: r["existing_italian_name"] for r in rows if r["existing_italian_name"]}
    assert aliases == {"Tortle": "Tortuga", "Tortle Druid": "Tortuga Druido"}
    assert sum(r["import_decision"] == "candidate_new" for r in rows) == 3
