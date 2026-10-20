"""Inventory-only check, not an import or verification of full monster mechanics."""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "scc_2021_en_source_inventory_45.json"


def test_strixhaven_census_and_source_lock():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "scc_2021_en"
    assert d["authority"]["physical_pdf_pages"] == 226
    assert d["authority"]["sha256"] == (
        "8f417ad08a68004869e141b1ab85e5659b95792250c8b82ddf70cb191f7c2063"
    )
    assert d["audit"]["bestiary_statblocks"] == 44
    assert d["audit"]["extra_outside_index_pdf_p159"] == 1
    assert d["audit"]["census_45"] == 45
    assert d["audit"]["database_writes"] == 0
    assert d["audit"]["core_statblocks_all_verified"] is False
    assert d["audit"]["original_pdf_or_ocr_text_published"] is False


def test_all_names_unique_and_outside_index_preserved():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    entries = d["entries"]
    assert len(entries) == 45
    assert len({e["name"].casefold() for e in entries}) == 45
    assert sum(e["census_index_page"] == 183 for e in entries) == 44
    assert all(e["completeness"] == "inventory_only" for e in entries)
    extra = [e for e in entries if e["name"] == "Scufflecup Teacup"]
    assert len(extra) == 1
    assert extra[0]["physical_pdf_page"] == 159
    assert extra[0]["source_inspected_core"]["hit_points"] == "5 (2d4)"
