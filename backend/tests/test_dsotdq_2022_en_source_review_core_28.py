"""Dragonlance source-locked independent monster and level-one sidekick cores."""
import json
import math
import re
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "dsotdq_2022_en_source_review_core_28.json"
SHA = "d867631c2344fbc8b1274478f01ad64e2f22989bf340b6b5ed8e001e63ce53a8"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
SIX = {"for", "des", "cos", "int", "sag", "car"}

def test_census_source_and_scope():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "dsotdq_2022_en"
    assert d["authority"]["sha256"] == SHA
    assert d["authority"]["physical_pdf_pages"] == 227
    assert d["audit"]["appendix_b_monsters_and_npcs"] == 22
    assert d["audit"]["appendix_c_sidekicks"] == 6
    assert d["audit"]["total_independent_statblocks"] == 28
    assert d["audit"]["db_writes_before_merge"] == 0
    assert d["audit"]["source_pdf_and_raw_ocr_not_committed"]
    assert not d["audit"]["full_actions_traits_spells_verified"]

def test_all_28_core_scores_hit_dice_and_pages():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    rows = d["statblocks"]
    assert len(rows) == len({x["name"].casefold() for x in rows}) == 28
    for r in rows:
        assert 194 <= r["physical_pdf_page"] <= 215
        assert r["physical_pdf_page"] - 2 == r["source_printed_page"]
        assert r["source_review"] == "original_pdf_text_and_visual"
        assert r["completeness"] == "statistiche_essenziali"
        assert 1 <= int(r["armor_class"].split()[0]) <= 30
        assert "ft." in r["speed"] and r["size_and_type"]
        assert set(r["ability_scores"]) == SIX
        assert all(1 <= s <= 30 for s in r["ability_scores"].values())
        m = DICE.fullmatch(r["hit_points"])
        assert m, r["name"]
        hp, count, die, sign, bonus = m.groups()
        avg = math.floor(int(count) * (int(die) + 1) / 2)
        avg += int(bonus or 0) * (-1 if sign == "-" else 1)
        assert int(hp) == avg, r["name"]
        if r["section"] == "sidekick_level_1":
            assert r["challenge_rating"] is None
            assert r["sidekick_level"] == 1
        else:
            assert re.fullmatch(r"(?:0|[1-9]\d*)(?:/[1-9]\d*)?", r["challenge_rating"])
            assert r["sidekick_level"] is None

def test_sidekicks_and_fidelity_to_visual_source():
    rows = {x["name"]: x for x in json.loads(PATH.read_text(encoding="utf-8"))["statblocks"]}
    assert len([x for x in rows.values() if x["section"] == "bestiary"]) == 22
    assert len([x for x in rows.values() if x["section"] == "sidekick_level_1"]) == 6
    assert rows["Hrigg Roundrook"]["armor_class"] == "16 (half plate)"
    assert rows["Caradoc"]["armor_class"] == "14"
    assert rows["Kender Skirmisher"]["armor_class"] == "14 (leather armor)"
    assert rows["Kansaldi Fire-Eyes"]["challenge_rating"] == "11"
    assert rows["Tem Temble"]["ability_scores"]["sag"] == 14
