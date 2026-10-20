"""The Tortle Package: 5 source-locked and mathematically checked monster cores."""
import json
import math
import re
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "data" / "tortle_2017_en_core_review.json"


def test_tortle_source_and_no_unverified_import():
    d = json.loads(P.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "tortle_2017_en"
    assert d["authority"]["sha256"] == (
        "3dea9cd685343b1d90207b2b79f4a963cb3131f30e67f23d10795ace8f9f1a44"
    )
    assert d["authority"]["physical_pdf_pages"] == 28
    assert d["audit"]["all_28_pdf_pages_surveyed"]
    assert d["audit"]["db_writes"] == 0
    assert d["audit"]["hp_hit_dice_math_checked"] == 5
    assert not d["audit"]["full_actions_traits_spells_verified"]
    assert not d["audit"]["marine_decapus_independent_statblock"]
    assert not d["audit"]["source_pdf_or_raw_ocr_in_repo"]


def test_five_page_scoped_cores():
    rows = json.loads(P.read_text(encoding="utf-8"))["statblocks"]
    assert len(rows) == 5
    assert len({r["name"].casefold() for r in rows}) == 5
    assert {r["physical_pdf_page"] for r in rows} == {21, 22, 23}
    assert {r["name"] for r in rows} == {
        "Decapus", "Geonid", "Topi", "Tortle", "Tortle Druid"
    }
    pattern = re.compile(r"^(\d+) \((\d+)d(\d+) \+ (\d+)\)$")
    for row in rows:
        assert row["completeness"] == "statistiche_essenziali"
        assert row["review_status"] == "source_core_verified_not_imported"
        assert set(row["ability_scores"]) == {"for", "des", "cos", "int", "sag", "car"}
        assert all(isinstance(v, int) and 1 <= v <= 30 for v in row["ability_scores"].values())
        assert isinstance(row["armor_class"], int) and 1 <= row["armor_class"] <= 30
        m = pattern.fullmatch(row["hit_points"])
        assert m is not None
        assert math.floor(int(m[2]) * (int(m[3]) + 1) / 2) + int(m[4]) == int(m[1])
