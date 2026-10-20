"""Source-locked mechanical core review for Explorer's Guide to Wildemount."""
import json
import math
import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "data" / "egtw_2020_en_source_review_core_29.json"
SHA = "15b34ddd1b33832fe2169821974d3a8d2de8470679ec49225e7e8669f029ce76"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
SIX = {"for", "des", "cos", "int", "sag", "car"}


def test_source_scope():
    d = json.loads(DOC.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "egtw_2020_en"
    assert d["authority"]["physical_pdf_pages"] == 307
    assert d["authority"]["sha256"] == SHA
    assert d["audit"]["independent_monster_and_npc_statblocks"] == 29
    assert d["audit"]["excluded_vehicle_name"] == "Stahlmaster"
    assert d["audit"]["hit_point_dice_arithmetic_verified"] == 29
    assert d["audit"]["database_writes"] == 0
    assert d["audit"]["original_pdf_ocr_not_committed"]
    assert not d["audit"]["full_traits_actions_spells_complete"]


def test_all_core_stats_and_dice():
    rows = json.loads(DOC.read_text(encoding="utf-8"))["statblocks"]
    assert len(rows) == len({r["name"].casefold() for r in rows}) == 29
    assert all(r["name"] != "Stahlmaster" for r in rows)
    for r in rows:
        assert 222 <= r["physical_pdf_page"] <= 302
        assert "ft." in r["speed"] and r["size_and_type"]
        assert 1 <= int(r["armor_class"].split()[0]) <= 30
        assert re.fullmatch(r"(0|[1-9]\d*)(/[1-9]\d*)?", r["challenge_rating"])
        assert set(r["ability_scores"]) == SIX
        assert all(1 <= v <= 30 for v in r["ability_scores"].values())
        assert r["completeness"] == "statistiche_essenziali"
        m = DICE.fullmatch(r["hit_points"])
        assert m, r["name"]
        hp, n, sides, sign, extra = m.groups()
        mean = math.floor(int(n) * (int(sides) + 1) / 2)
        mean += int(extra or 0) * (-1 if sign == "-" else 1)
        assert int(hp) == mean, r["name"]


def test_source_visual_anomalies_kept():
    rows = {r["name"]: r for r in json.loads(DOC.read_text(encoding="utf-8"))["statblocks"]}
    assert rows["Core Spawn Crawler"]["ability_scores"]["car"] == 6
    assert rows["Core Spawn Crawler"]["physical_pdf_page"] == 287
    assert rows["Bol'bara"]["size_and_type"].startswith("Small humanoid (goblinoid)")
    assert "15 with mage armor" in rows["Bol'bara"]["armor_class"]
    assert rows["Horizonback Tortoise"]["armor_class"].endswith(
        "22 while in its shell"
    )
    assert rows["Kobold Underling"]["challenge_rating"] == "1/8"
