"""Source-locked mechanical-core checks for The Book of Many Things (2023)."""

import csv
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data"
TABLE = ROOT / "bomt_2023_en_verified_core_36.tsv"
SCOPE = ROOT / "bomt_2023_en_source_review_scope.json"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
CR = re.compile(r"^(?:0|[1-9]\d*)(?:/[1-9]\d*)?$")
SIX = ("for", "des", "cos", "int", "sag", "car")


def _rows():
    with TABLE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_source_sha_and_scope_are_fail_closed():
    d = json.loads(SCOPE.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "bomt_2023_en"
    assert d["authority"]["physical_pdf_pages"] == 195
    assert d["authority"]["physical_sha256"] == (
        "6dd24843c9766ad10d3a6098afb90de0680bf285efc0f73b9fa281085b946146"
    )
    assert d["audit"]["index_pdf_page"] == 176
    assert d["audit"]["indexed_monster_statblocks"] == 35
    assert d["audit"]["total_statblocks"] == 36
    assert d["audit"]["fixed_core_verified"] == 35
    assert d["audit"]["dynamic_core_formula_preserved"] == 1
    assert d["audit"]["database_writes_before_ci"] == 0
    assert not d["audit"]["full_actions_traits_spells_verified"]
    assert d["audit"]["original_pdf_ocr_text_not_committed"]


def test_all_36_core_statblocks_and_average_hit_dice():
    rows = _rows()
    assert len(rows) == 36
    assert len({r["name"].casefold() for r in rows}) == 36
    assert len({r["name"] for r in rows if r["challenge_rating"] == "—"}) == 1
    for r in rows:
        assert len(r) == 13
        assert 1 <= int(r["page"]) <= 195
        assert 1 <= int(r["armor_class"].split()[0]) <= 30
        assert "ft." in r["speed"]
        assert r["size_and_type"]
        assert all(1 <= int(r[key]) <= 30 for key in SIX)
        if r["name"] == "Deck Defender":
            assert r["page"] == "73"
            assert r["challenge_rating"] == "—"
            assert r["hit_points"].startswith("5 + five times your level")
            assert "d8 Hit Dice" in r["hit_points"]
            continue
        assert CR.fullmatch(r["challenge_rating"])
        match = DICE.fullmatch(r["hit_points"])
        assert match, r["name"]
        hp, count, size, sign, mod = match.groups()
        average = math.floor(int(count) * (int(size) + 1) / 2)
        average += (-1 if sign == "-" else 1) * int(mod or 0)
        assert average == int(hp), r["name"]


def test_outside_index_and_conditional_armor_classes():
    items = {r["name"]: r for r in _rows()}
    assert items["Aspirant of the Comet"]["hit_points"] == "27 (5d8 + 5)"
    assert items["Minotaur Infiltrator"]["page"] == "128"
    assert items["Brusipha"]["page"] == "128"
    assert items["Veiled Presence"]["hit_points"] == "300 (40d8 + 120)"
    assert items["Grim Champion of Desolation"]["hit_points"] == "416 (49d8 + 196)"
    assert items["Euryale"]["hit_points"] == "297 (35d8 + 140)"
    assert items["Grim Champion of Pestilence"]["armor_class"] == (
        "14 (17 with Mage Armor)"
    )
    assert items["Enchanting Infiltrator"]["armor_class"] == (
        "18 (Veiled Presence)"
    )
