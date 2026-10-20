"""Planescape inventory only; must not be imported as verified mechanical cores."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "planescape_2023_source_inventory_54.json"


def test_physical_source_and_three_distinct_logical_sections():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    a = d["authority"]
    assert a["physical_pages"] == 262
    assert a["physical_sha256"] == "61392d7a3ab2241dce67b1027c4830e0b3e9431d224f5a1619c6f5257bd427b1"
    assert set(a["logical_source_ids"]) == {
        "ps_sigil_2023_en", "ps_tofw_2023_en", "ps_mpp_2023_en"
    }
    assert d["audit"]["statblock_cr_index_pdf_page"] == 202
    assert d["audit"]["statblock_cr_index_count"] == 53
    assert d["audit"]["morte_outside_index_pdf_page"] == 109
    assert d["audit"]["provisional_independent_statblocks"] == 54
    assert not d["audit"]["all_other_core_stats_checked"]
    assert not d["audit"]["other_outside_index_statblocks_exhaustively_excluded"]
    assert d["audit"]["db_writes"] == 0
    assert not d["audit"]["original_pdf_or_ocr_committed"]


def test_all_index_names_are_distinct_and_morte_is_extra():
    entries = json.loads(DATA.read_text(encoding="utf-8"))["entries"]
    assert len(entries) == 54
    assert len({e["name"].casefold() for e in entries}) == 54
    assert sum(e["logical_source_id"] == "ps_mpp_2023_en" for e in entries) == 53
    assert sum(e["review_phase"] == "index_census_not_source_verified" for e in entries) == 53
    morte = [e for e in entries if e["name"] == "Morte"]
    assert len(morte) == 1
    assert morte[0]["physical_pdf_page"] == 109
    assert morte[0]["hit_points"] == "22 (4d4 + 12)"
    assert morte[0]["challenge_rating_index"] == "1/4"
