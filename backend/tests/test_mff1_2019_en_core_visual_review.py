"""Fail-closed regression for MFF1 PDF core review only.

The survey provides source-locked core fields and NEVER writes to a database.
"""

import json
import math
import re
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "mff1_2019_en_core_visual_review.json"
)
EXPECTED_SHA = "e84ea509258d5d96dbb5d5253accc694f658b1985d66257a1be913b54faeec4a"
DICE = re.compile(r"^(\d+) \((\d+)d(\d+)(?: ([+-]) (\d+))?\)$")
STATS = {"for", "des", "cos", "int", "sag", "car"}


def test_review_only_catalogue_and_provenance():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert doc["authority"]["sha256"] == EXPECTED_SHA
    assert doc["authority"]["physical_pdf_pages"] == 22
    assert doc["authority"]["logical_source_id"] == "mff1_2019_en"
    assert doc["audit"]["database_writes"] == 0
    assert doc["audit"]["integral_actions_complete"] is False
    assert doc["audit"]["total_distinct_statblocks"] == 18
    assert len(doc["statblocks"]) == 18
    assert len({x["name"].casefold() for x in doc["statblocks"]}) == 18
    assert doc["audit"]["manual_inventory_pages"] == [
        x["physical_pdf_page"] for x in doc["statblocks"]
    ]


def test_all_eighteen_page_scoped_core_fields_are_mathematically_coherent():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    for record in doc["statblocks"]:
        assert 1 <= record["physical_pdf_page"] <= 22
        assert record["source_review"] == "original_pdf_page_visual"
        assert record["review_status"] == "source_reviewed_not_imported"
        assert record["completeness"] == "statistiche_essenziali"
        assert record["armor_class"] and record["speed"]
        assert set(record["ability_scores"]) == STATS
        assert all(1 <= score <= 30 for score in record["ability_scores"].values())
        assert re.match(r"^(?:[0-9]+(?:/[0-9]+)?)$", record["challenge_rating"])
        match = DICE.fullmatch(record["hit_points"])
        assert match is not None, record["name"]
        hp, count, sides, sign, bonus = match.groups()
        assert int(sides) in {4, 6, 8, 10, 12, 20}
        offset = int(bonus or 0) * (-1 if sign == "-" else 1)
        assert int(hp) == math.floor(int(count) * (int(sides) + 1) / 2) + offset


def test_distinct_named_variants_are_not_collapsed():
    records = json.loads(SOURCE.read_text(encoding="utf-8"))["statblocks"]
    names = {x["name"] for x in records}
    assert {"Norker", "Norker War Leader", "Needle Spawn", "Needle Lord"} <= names
    assert next(x for x in records if x["name"] == "Ygorl, Lord of Entropy")[
        "physical_pdf_page"
    ] == 21
