"""Validate Ravnica's source-locked 78 creature mechanical statblock cores."""
import json
import math
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "ggtr_2018_en_source_review_core_78.json"
SHA = "857059410acb8db20bf01e78fe0432e8f2a35948ed70db2ebdaaa3c1ab017956"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
SCORES = {"for", "des", "cos", "int", "sag", "car"}


def test_source_and_scope():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    assert doc["authority"]["logical_source_id"] == "ggtr_2018_en"
    assert doc["authority"]["sha256"] == SHA
    assert doc["authority"]["physical_pdf_pages"] == 258
    assert doc["audit"]["independent_source_statblocks"] == 78
    assert doc["audit"]["hp_hit_die_average_validated"] == 78
    assert doc["audit"]["adventure_statblocks"] == 3
    assert doc["audit"]["chapter6_monster_and_npc_statblocks"] == 75
    assert doc["audit"]["database_writes_in_manifest"] == 0
    assert not doc["audit"]["full_traits_actions_spells_complete"]
    assert doc["audit"]["source_pdf_and_ocr_not_committed"]


def test_all_78_core_stats_and_dice():
    rows = json.loads(DATA.read_text(encoding="utf-8"))["statblocks"]
    assert len(rows) == len({r["name"].casefold() for r in rows}) == 78
    assert sum(168 <= r["physical_pdf_page"] <= 171 for r in rows) == 3
    assert sum(190 <= r["physical_pdf_page"] <= 257 for r in rows) == 75
    for r in rows:
        assert r["name"] and r["size_and_type"] and "ft." in r["speed"]
        assert 1 <= int(r["armor_class"].split()[0]) <= 30
        assert set(r["ability_scores"]) == SCORES
        assert all(1 <= v <= 30 for v in r["ability_scores"].values())
        assert re.fullmatch(r"(?:0|[1-9]\d*)(?:/[1-9]\d*)?", r["challenge_rating"])
        m = DICE.fullmatch(r["hit_points"])
        assert m, r["name"]
        hp, count, die, sign, bonus = m.groups()
        computed = math.floor(int(count) * (int(die) + 1) / 2)
        computed += int(bonus or 0) * (-1 if sign == "-" else 1)
        assert computed == int(hp), r["name"]


def test_fractional_cr_and_original_ambiguities():
    d = {x["name"]: x for x in json.loads(DATA.read_text(encoding="utf-8"))["statblocks"]}
    assert d["Goblin Gang Member"]["challenge_rating"] == "1/4"
    assert d["Frontline Medic"]["challenge_rating"] == "1/4"
    assert d["Cackler"]["challenge_rating"] == "1/2"
    assert d["Jarad vod Savo"]["ability_scores"]["car"] == 15
    assert d["Aurelia"]["ability_scores"]["cos"] == 25
    assert d["Archon of the Triumvirate"]["ability_scores"]["des"] == 15
    assert d["Blistercoil Weird"]["ability_scores"]["int"] == 5
    assert d["Skyswimmer"]["speed"].startswith("10 ft.")
    assert "plus 1" in d["Obzedat Ghost"]["armor_class"]
