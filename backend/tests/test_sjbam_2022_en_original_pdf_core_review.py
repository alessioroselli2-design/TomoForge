"""Fail-closed original-PDF core review: Boo's Astral Menagerie."""

import json
import math
import re
from pathlib import Path

FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "sjbam_2022_en_original_pdf_core_review.json"
)
SOURCE_SHA = "24c0025969bbeb09e01fbf7ed7969ce2e21d2926a6f4e5f4b1c566d0597e067e"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
ABILITY_NAMES = {"for", "des", "cos", "int", "sag", "car"}
SIZES = {"Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"}


def test_source_pin_conservative_review_and_scope():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    src, audit = data["authority"], data["audit"]
    assert src["logical_source_id"] == "sjbam_2022_en"
    assert src["sha256"] == SOURCE_SHA
    assert src["physical_pdf_pages"] == 66
    assert src["language"] == "en"
    assert audit["index_page"] == 5
    assert audit["total_index_statblocks"] == 72
    assert audit["source_reviewed_core"] == 72
    assert audit["hp_dice_math_checked"] == 72
    assert audit["all_six_ability_scores_visually_checked"] == 72
    assert audit["ocr_max_window_pages"] <= 12
    assert audit["database_writes"] == 0
    assert audit["translation_pending"] is True
    assert audit["complete_statblock_actions_traits_spells"] is False
    assert audit["original_pdf_or_raw_ocr_in_repo"] is False


def test_72_distinct_page_scoped_monster_cores_and_exact_hp_dice_arithmetic():
    rows = json.loads(FILE.read_text(encoding="utf-8"))["statblocks"]
    assert len(rows) == 72
    assert len({row["name"].casefold() for row in rows}) == 72
    for row in rows:
        assert 8 <= row["physical_pdf_page"] <= 64
        assert row["size"] in SIZES
        assert isinstance(row["armor_class"], int) and 1 <= row["armor_class"] <= 30
        assert re.match(r"^\d+ ft\.", row["speed"])
        assert set(row["ability_scores"]) == ABILITY_NAMES
        assert all(
            isinstance(score, int) and 1 <= score <= 30
            for score in row["ability_scores"].values()
        )
        assert re.fullmatch(r"(0|[1-9]\d*)(/[1-9]\d*)?", row["challenge_rating"])
        assert row["review_status"] == "source_core_verified_not_imported"
        assert row["completeness"] == "statistiche_essenziali"
        match = DICE.fullmatch(row["hit_points"])
        assert match is not None, row["name"]
        hp, count, die, sign, modifier = match.groups()
        expected = math.floor(int(count) * (int(die) + 1) / 2)
        expected += int(modifier or 0) * (-1 if sign == "-" else 1)
        assert int(hp) == expected, row["name"]


def test_distinct_creature_forms_are_never_conflated():
    rows = json.loads(FILE.read_text(encoding="utf-8"))["statblocks"]
    by_name = {row["name"]: row for row in rows}
    assert by_name["Githyanki xenomancer"]["physical_pdf_page"] == 27
    assert by_name["Vampirate"]["physical_pdf_page"] == 62
    assert by_name["Gaj"]["physical_pdf_page"] == 23
    assert by_name["Feyr"]["physical_pdf_page"] == 22
    assert by_name["Cosmic horror"]["physical_pdf_page"] == 18
    assert by_name["Space swine"]["armor_class_qualifier"]
    assert by_name["Braxat"]["armor_class_qualifier"]
    assert by_name["Ssurran defiler"]["armor_class_qualifier"]
