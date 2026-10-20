"""Source-locked core audit for 15 Locathah Rising stat blocks."""
import json
import math
import re
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "data" / "locathah_2019_en_source_review_core.json"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
SCORES = {"for", "des", "cos", "int", "sag", "car"}


def test_locathah_source_lock_and_scope():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["authority"]["logical_source_id"] == "locathah_2019_en"
    assert manifest["authority"]["physical_pdf_pages"] == 39
    assert manifest["authority"]["sha256"] == (
        "8c2a0a17510fc84628534cd832ae171bade87460c6b22a48cc12b4fd48cd47a6"
    )
    assert manifest["audit"]["new_candidates"] == 13
    assert manifest["audit"]["existing_canonical_aliases"] == 2
    assert manifest["audit"]["source_statblocks"] == 15
    assert manifest["audit"]["integral_actions_traits_spells_complete"] is False
    assert manifest["audit"]["no_database_write_from_manifest"]
    assert manifest["audit"]["source_pdf_and_raw_ocr_excluded"]


def test_each_core_and_hit_die_average_agrees_with_source():
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))["statblocks"]
    assert len(rows) == 15
    assert len({r["name"].casefold() for r in rows}) == 15
    for r in rows:
        assert 15 <= r["physical_pdf_page"] <= 23
        assert r["source_review"] == "original_pdf_text_and_layout"
        assert r["completeness"] == "statistiche_essenziali"
        assert 1 <= r["armor_class"] <= 30
        assert r["speed"] and r["size_and_type"]
        assert re.fullmatch(r"(?:0|[1-9]\d*)(?:/[1-9]\d*)?", r["challenge_rating"])
        assert set(r["ability_scores"]) == SCORES
        assert all(1 <= x <= 30 for x in r["ability_scores"].values())
        hp = DICE.fullmatch(r["hit_points"])
        assert hp, r["name"]
        avg, num, size, sign, mod = hp.groups()
        computed = math.floor(int(num) * (int(size) + 1) / 2)
        computed += int(mod or 0) * (-1 if sign == "-" else 1)
        assert int(avg) == computed, r["name"]


def test_aliases_and_source_anomalies_not_silently_removed():
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))["statblocks"]
    aliases = {r["name"]: r["existing_name"] for r in rows if r["existing_name"]}
    assert aliases == {
        "Giant Shark": "Squalo Gigante",
        "Water Elemental Myrmidon": "Mirmidone Elementale D'Acqua",
    }
    names = {r["name"]: r for r in rows}
    assert sum(r["import_decision"] == "candidate_new" for r in rows) == 13
    assert names["Fhenimore (Kraken Priest Variant)"]["ability_scores"]["for"] == 13
    assert "source_discrepancy" in names["Fhenimore (Kraken Priest Variant)"]
    assert names["Shoalar Quaderil"]["challenge_rating"] == "6"
    assert "source_discrepancy" in names["Shoalar Quaderil"]
