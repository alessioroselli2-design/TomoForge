"""Acquisitions Incorporated: verify source-locked original monster/NPC cores."""
import json
import math
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "ai_2019_en_source_review_core_21.json"
SHA = "8066053a30443f5e4cd7e819e2aeff63d280af1ad0cbebc776d743cb3ee8b94d"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
SIX = {"for", "des", "cos", "int", "sag", "car"}


def test_source_and_scope():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "ai_2019_en"
    assert d["authority"]["sha256"] == SHA
    assert d["authority"]["physical_pdf_pages"] == 226
    assert d["audit"]["appendix_A_NPCs"] == 15
    assert d["audit"]["appendix_B_monsters"] == 6
    assert d["audit"]["monster_and_npc_statblocks"] == 21
    assert d["audit"]["all_hit_dice_arithmetic_verified"] == 21
    assert d["audit"]["vehicle_statblocks_excluded"]
    assert d["audit"]["database_writes_before_merge"] == 0
    assert not d["audit"]["full_actions_traits_spells_complete"]
    assert not d["audit"]["raw_ocr_or_pdf_committed"]


def test_all_unique_valid_statblocks():
    r = json.loads(DATA.read_text(encoding="utf-8"))["statblocks"]
    assert len(r) == 21
    assert len({x["name"].casefold() for x in r}) == 21
    for x in r:
        assert 197 <= x["physical_pdf_page"] <= 214
        assert x["source_review"] == "original_pdf_visual_and_text"
        assert x["completeness"] == "statistiche_essenziali"
        assert x["size_and_type"] and x["speed"]
        assert 1 <= int(x["armor_class"].split()[0]) <= 30
        assert re.fullmatch(r"(0|[1-9]\d*)(/[1-9]\d*)?", x["challenge_rating"])
        assert set(x["ability_scores"]) == SIX
        assert all(1 <= v <= 30 for v in x["ability_scores"].values())
        m = DICE.fullmatch(x["hit_points"])
        assert m is not None, x["name"]
        hp, count, size, sign, bonus = m.groups()
        computed = math.floor(int(count) * (int(size) + 1) / 2)
        computed += int(bonus or 0) * (-1 if sign == "-" else 1)
        assert int(hp) == computed, x["name"]


def test_source_visual_corrections_are_preserved():
    rows = {
        r["name"]: r for r in json.loads(DATA.read_text(encoding="utf-8"))["statblocks"]
    }
    assert rows["Omin Dran"]["armor_class"] == "18 (plate)"
    assert rows["Jim Darkmagic"]["challenge_rating"] == "5"
    assert rows["Deep Crow"]["hit_points"] == "133 (14d10 + 56)"
    assert rows["Ancient Deep Crow"]["hit_points"] == "187 (15d12 + 90)"
    assert rows["Splugoth the Returned"]["armor_class"] == "15 (natural armor)"
    assert rows["Clockwork Dragon"]["challenge_rating"] == "1"
