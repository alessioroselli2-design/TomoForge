"""Fizban: fail-closed check of the 73-page-scoped core statblocks."""
import json
import math
import re
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "ftod_2021_it_visual_inventory_73.json"
SHA = "f844e50d4c69ba2989bd7e221bbe70038e0a56f25cc3eada1825933ce0d4547a"
DICE = re.compile(r"^(\d+) \((\d+)d(\d+)(?: ([+-]) (\d+))?\)$")
ABILITIES = {"for", "des", "cos", "int", "sag", "car"}


def test_source_lock_no_licensed_material_or_database_side_effects():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "ftod_2021_it"
    assert d["authority"]["sha256"] == SHA
    assert d["authority"]["physical_pdf_pages"] == 227
    assert d["audit"]["source_review_only"]
    assert d["audit"]["db_writes"] == 0
    assert not d["audit"]["integral_actions_traits_spells_complete"]
    assert not d["audit"]["source_pdf_or_raw_ocr_in_repo"]
    assert d["audit"]["ocr_window_size_max"] <= 12
    assert d["audit"]["source_reviewed_core"] == 73
    assert d["audit"]["bestiary_statblocks"] == 70
    assert d["audit"]["outside_bestiary_statblocks"] == 3


def test_unique_and_compatible_core_and_hp_dice_math():
    rows = json.loads(PATH.read_text(encoding="utf-8"))["statblocks"]
    assert len(rows) == 73
    assert len({r["name"].casefold() for r in rows}) == 73
    dynamic_count = 0
    for r in rows:
        assert 1 <= r["physical_pdf_page"] <= 227
        assert r["review_status"] == "source_core_verified_not_imported"
        assert r["completeness"] == "statistiche_essenziali"
        assert set(r["ability_scores"]) == ABILITIES
        assert all(isinstance(v, int) and 1 <= v <= 30 for v in r["ability_scores"].values())
        assert r["armor_class"] and r["hit_points"] and r["speed"]
        if r.get("dynamic_core"):
            dynamic_count += 1
            assert r["name"] in {"Compagno Drago", "Spirito Draconico"}
            assert r["challenge_rating"] == "—"
            assert "livello" in r["hit_points"]
            assert r["hit_dice_variable"]
            continue
        assert re.fullmatch(r"(?:0|[1-9]\d*)(?:/[1-9]\d*)?", r["challenge_rating"])
        m = DICE.fullmatch(r["hit_points"])
        assert m is not None, r["name"]
        hp, n, die, sign, modifier = m.groups()
        expected = math.floor(int(n) * (int(die) + 1) / 2)
        expected += int(modifier or 0) * (-1 if sign == "-" else 1)
        assert int(hp) == expected, r["name"]
    assert dynamic_count == 2


def test_named_forms_and_physical_pages():
    rows = json.loads(PATH.read_text(encoding="utf-8"))["statblocks"]
    by_name = {r["name"]: r for r in rows}
    assert by_name["Creazione di Bahamut"]["physical_pdf_page"] == 165
    assert by_name["Grande dragone gemma"]["physical_pdf_page"] == 207
    assert by_name["Grande dragone metallico"]["physical_pdf_page"] == 209
    assert by_name["Reliquia draconica"]["physical_pdf_page"] == 215
    assert by_name["Compagno Drago"]["physical_pdf_page"] == 16
    assert by_name["Spirito Draconico"]["physical_pdf_page"] == 21
    assert by_name["Canarino Gigante"]["physical_pdf_page"] == 25
    assert by_name["Soffio animato"]["conditional_ac_note"]
