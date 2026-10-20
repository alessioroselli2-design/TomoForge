"""Source-locked Fizban full-PDF census; this is not an import."""
import json
from pathlib import Path

PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "ftod_2021_it_visual_inventory_73.json"
)


def test_fizban_inventory_is_source_locked_and_unique():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "ftod_2021_it"
    assert d["authority"]["sha256"] == (
        "f844e50d4c69ba2989bd7e221bbe70038e0a56f25cc3eada1825933ce0d4547a"
    )
    assert d["authority"]["physical_pdf_pages"] == 227
    assert d["authority"]["index_physical_page"] == 225
    assert d["audit"]["database_writes"] == 0
    assert d["audit"]["core_stats_complete"] is False
    assert d["audit"]["integral_statblocks_complete"] is False
    records = d["index"]
    assert len(records) == 73
    assert len({r["name"].casefold() for r in records}) == 73
    assert len([r for r in records if r["source_status"] == "outside_bestiary_visual_review"]) == 3
    assert len([r for r in records if r["source_status"] == "index_and_visual_page_corroborated"]) == 70
    assert all(1 <= r["physical_pdf_page"] <= 225 for r in records)
    assert all(r["completeness"] == "inventory_only_core_pending" for r in records)


def test_dynamic_statblocks_not_converted_to_fake_fixed_stats():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    records = {r["name"]: r for r in d["index"]}
    assert records["Compagno Drago"]["dynamic_stats"] is True
    assert records["Spirito Draconico"]["dynamic_stats"] is True
    assert records["Compagno Drago"]["challenge_rating"] == "—"
    assert records["Spirito Draconico"]["challenge_rating"] == "—"
    assert records["Canarino Gigante"]["visual_verified_core"][
        "hit_points"
    ] == "26 (4d10 + 4)"
