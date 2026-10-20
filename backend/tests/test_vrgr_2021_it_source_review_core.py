"""Fail-closed regression for Van Richten's page-indexed core-statblock survey.

This checks a *review-only* source manifest. It never creates database records.
"""
import json
import re
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "vrgr_2021_it_source_review_core.json"
)
SHA = "7d8e6479f592df1630fc3abb02d3612a1d8514b3faff8d558288005185980209"
HIT_DICE = re.compile(
    r"^(\d+)\s*\((\d+)d(\d+)(?:\s*([+-])\s*(\d+))?\)$"
)
ABILITIES = {"for", "des", "cos", "int", "sag", "car"}


def test_source_review_manifest_has_36_distinct_blocks_and_correct_scope():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert data["authority"]["sha256"] == SHA
    assert data["authority"]["physical_pages"] == 257
    audit = data["audit"]
    assert audit["bestiary_index_statblocks"] == 32
    assert audit["outside_index_statblocks"] == 4
    assert audit["new_source_review_candidates"] == 35
    assert audit["database_writes"] == 0
    assert audit["original_manual_is_complete"] is False
    assert audit["actions_and_traits_complete"] is False
    blocks = data["statblocks"]
    assert len(blocks) == 36
    assert len({x["name"].casefold() for x in blocks}) == 36
    assert sum(x["page"] == 201 for x in blocks) == 4
    assert (
        sum(x["review_status"] == "already_imported_core_verified" for x in blocks)
        == 1
    )


def test_every_source_visual_block_has_coherent_exact_core_stats():
    blocks = json.loads(SOURCE.read_text(encoding="utf-8"))["statblocks"]
    for record in blocks:
        assert record["source_review"] == "original_scanned_page_visual"
        assert record["completeness"] == "statistiche_essenziali"
        assert 1 <= record["page"] <= 257
        assert record["armor_class"] and record["speed"]
        assert set(record["ability_scores"]) == ABILITIES
        assert all(1 <= value <= 30 for value in record["ability_scores"].values())
        m = HIT_DICE.fullmatch(record["hit_points"])
        assert m is not None, record["name"]
        hp, count, die, sign, modifier = m.groups()
        assert int(die) in {4, 6, 8, 10, 12, 20}
        offset = int(modifier or 0) * (-1 if sign == "-" else 1)
        assert int(hp) == (int(count) * (int(die) + 1)) // 2 + offset
        if record["page"] == 201:
            assert record["challenge_rating"] == "—"
        else:
            assert record["challenge_rating"] != "—"


def test_duplicate_spia_is_a_distinct_variant_not_merge_by_name():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    block = next(x for x in doc["statblocks"] if x["name"] == "Spia")
    assert block["page"] == 201
    assert block["hit_points"] == "9 (2d6 + 2)"
    assert block["challenge_rating"] == "—"
    assert any(
        "Spia" in note and "differs" in note.lower()
        for note in doc["collision_notes"]
    )
