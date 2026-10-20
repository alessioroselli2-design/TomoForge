"""Validate Planescape's source-locked index, without accepting index-only candidates."""
import json
import math
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "ps_mpp_2023_en_source_inventory_54.json"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
SCORES = {"for", "des", "cos", "int", "sag", "car"}


def test_authority_and_index():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    assert doc["authority"]["logical_source_id"] == "ps_mpp_2023_en"
    assert doc["authority"]["sha256"] == "61392d7a3ab2241dce67b1027c4830e0b3e9431d224f5a1619c6f5257bd427b1"
    assert doc["authority"]["physical_page_start"] == 197
    assert doc["authority"]["physical_page_end"] == 262
    rows = doc["index"]
    assert len(rows) == doc["audit"]["statblocks_indexed"] == 54
    assert len({row["name"].casefold() for row in rows}) == 54
    assert all(row["physical_pdf_page"] == row["printed_page"] + 197 for row in rows)
    assert all(213 <= row["physical_pdf_page"] <= 259 for row in rows)
    assert not doc["audit"]["english_italian_cross_language_dedup_checked"]
    assert not doc["audit"]["full_traits_actions_spells_complete"]
    assert doc["audit"]["database_writes_in_manifest"] == 0


def test_visual_core_review_only():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    cores = doc["reviewed_core_statblocks"]
    reviewed_names = {
        row["name"]
        for row in doc["index"]
        if row["core_review_status"] == "source_core_reviewed"
    }
    assert len(cores) == doc["audit"]["independent_core_fields_visually_verified"] == 2
    assert {r["name"] for r in cores} == reviewed_names
    assert {r["name"] for r in cores} == {"Equinal Guardinal", "Musteval Guardinal"}
    for row in cores:
        assert row["physical_pdf_page"] == 230
        assert 1 <= int(row["armor_class"].split()[0]) <= 30
        assert set(row["ability_scores"]) == SCORES
        assert all(1 <= x <= 30 for x in row["ability_scores"].values())
        assert "ft." in row["speed"]
        m = DICE.fullmatch(row["hit_points"])
        assert m, row["name"]
        hp, count, die, sign, bonus = m.groups()
        average = math.floor(int(count) * (int(die) + 1) / 2)
        average += int(bonus or 0) * (-1 if sign == "-" else 1)
        assert average == int(hp), row["name"]
