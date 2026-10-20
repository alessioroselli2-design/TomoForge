"""Fail-closed regression for 72 source-reviewed Boo's Astral Menagerie cores."""

import json
import math
import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "data" / "sjbam_2022_en_source_review_core.json"
SHA = "24c0025969bbeb09e01fbf7ed7969ce2e21d2926a6f4e5f4b1c566d0597e067e"
ABILITIES = {"for", "des", "cos", "int", "sag", "car"}


def test_provenance_and_scope():
    d = json.loads(DOC.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "sjbam_2022_en"
    assert d["authority"]["physical_pdf_pages"] == 66
    assert d["authority"]["sha256"] == SHA
    assert d["audit"]["count_index"] == 72
    assert d["audit"]["total_source_statblocks"] == 72
    assert d["audit"]["database_writes"] == 0
    assert not d["audit"]["actions_traits_spells_verified"]
    assert d["audit"]["statblock_core_only"]
    assert d["audit"]["page_window_limit"] <= 12
    assert d["audit"]["source_pdf_and_ocr_not_committed"]
    assert d["audit"]["translation_status"] == "processing"


def test_all_72_core_fields_and_hit_dice_arithmetic():
    rows = json.loads(DOC.read_text(encoding="utf-8"))["statblocks"]
    assert len(rows) == 72
    assert len({r["name"].casefold() for r in rows}) == 72
    for r in rows:
        assert 6 <= r["physical_pdf_page"] <= 65
        assert r["completezza_scheda"] == "statistiche_essenziali"
        assert r["review_status"] == "source_core_verified_not_imported"
        assert r["size"] in {"Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"}
        assert r["creature_type"]
        assert isinstance(r["armor_class"], int) and 1 <= r["armor_class"] <= 30
        assert re.search(r"\d+ ft\.", r["speed"])
        assert set(r["ability_scores"]) == ABILITIES
        assert all(1 <= x <= 30 for x in r["ability_scores"].values())
        assert re.fullmatch(r"(?:0|[1-9]\d*)(?:/[1-9]\d*)?", r["challenge_rating"])
        m = re.fullmatch(r"(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)", r["hit_points"])
        assert m is not None, r["name"]
        hp, count, sides, sign, bonus = m.groups()
        expected = math.floor(int(count) * (int(sides) + 1) / 2)
        expected += (-1 if sign == "-" else 1) * int(bonus or 0)
        assert expected == int(hp), r["name"]


def test_named_variants_remain_distinct():
    names = {r["name"] for r in json.loads(DOC.read_text(encoding="utf-8"))["statblocks"]}
    assert {"Space hamster", "Giant space hamster", "Aartuk priest", "Aartuk warrior", "Aartuk elder", "Lunar dragon wyrmling", "Young lunar dragon", "Adult lunar dragon", "Ancient lunar dragon", "Solar dragon wyrmling", "Young solar dragon", "Adult solar dragon", "Ancient solar dragon"} <= names
