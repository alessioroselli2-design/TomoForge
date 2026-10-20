"""Source-locked checks for Strixhaven's 45 mechanically reviewed creatures."""
import csv
import json
import math
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "data"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
SIX = ("for", "des", "cos", "int", "sag", "car")


def _records():
    with (BASE / "scc_2021_en_verified_core_45.tsv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def test_source_identity_and_scope():
    d = json.loads((BASE / "scc_2021_en_source_review_scope.json").read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "scc_2021_en"
    assert d["authority"]["physical_pages"] == 226
    assert d["authority"]["physical_sha256"] == "8f417ad08a68004869e141b1ab85e5659b95792250c8b82ddf70cb191f7c2063"
    assert d["audit"]["count_total"] == 45
    assert d["audit"]["chapter7_index_total"] == 44
    assert d["audit"]["hit_dice_checked"] == 45
    assert d["audit"]["database_writes"] == 0
    assert d["audit"]["original_pdf_not_committed"]
    assert d["audit"]["all_core_source_verified"]
    assert not d["audit"]["integral_traits_actions_spells_verified"]
    assert not d["audit"]["translation_verified"]


def test_unique_and_valid_mechanical_cores():
    rows = _records()
    assert len(rows) == len({r["name"].casefold() for r in rows}) == 45
    assert sum(int(r["page"]) == 159 for r in rows) == 1
    assert sum(184 <= int(r["page"]) <= 223 for r in rows) == 44
    for r in rows:
        assert len(r) == 13
        assert 1 <= int(r["armor_class"].split()[0]) <= 30
        assert "ft." in r["speed"] and r["size_and_type"]
        assert re.fullmatch(r"(?:0|[1-9]\d*)(?:/[1-9]\d*)?", r["challenge_rating"])
        assert all(1 <= int(r[k]) <= 30 for k in SIX)
        m = DICE.fullmatch(r["hit_points"])
        assert m is not None, r["name"]
        hp, n, sides, sign, offset = m.groups()
        value = math.floor(int(n) * (int(sides) + 1) / 2)
        value += (-1 if sign == "-" else 1) * int(offset or 0)
        assert value == int(hp), r["name"]


def test_edge_cases_and_named_versions():
    x = {r["name"]: r for r in _records()}
    assert x["Scufflecup Teacup"]["hit_points"] == "5 (2d4)"
    assert x["Beledros Witherbloom"]["hit_points"] == "444 (24d20 + 192)"
    assert x["Velomachus Lorehold"]["hit_points"] == "487 (25d20 + 225)"
    assert x["Witherbloom Pledgemage"]["armor_class"] == "12 (15 with Vociferous Form)"
    assert x["Lorehold Pledgemage"]["armor_class"] == "13 (16 with mage armor)"
    assert sum(" Professor of " in name for name in x) == 10
