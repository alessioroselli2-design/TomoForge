"""Source-locked visual review of Light of Xaryxis's monster statblock."""
import json
import math
import re
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "data" / "sjlox_2022_en_source_review_core.json"


def test_source_and_scope():
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert doc["authority"]["logical_source_id"] == "sjlox_2022_en"
    assert doc["authority"]["physical_pdf_pages"] == 66
    assert doc["authority"]["sha256"] == (
        "5eeed29e1cf55adad7ae984a947c5ba6f5a2854e254a6a2b9988e6ffb4d54421"
    )
    assert doc["audit"]["all_pdf_pages_visually_screened"] == 66
    assert doc["audit"]["autonomous_statblocks"] == 1
    assert doc["audit"]["new_creatures"] == 1
    assert doc["audit"]["db_writes"] == 0
    assert not doc["audit"]["full_traits_actions_spells_verified"]
    assert not doc["audit"]["source_pdf_or_raw_ocr_in_public_repo"]


def test_astral_blight_core_is_coherent():
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = doc["statblocks"]
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "Astral Blight"
    assert row["physical_pdf_page"] == 11
    assert row["size_and_type"] == "Medium plant, unaligned"
    assert row["armor_class"] == 12
    assert row["speed"] == "10 ft."
    assert row["challenge_rating"] == "1"
    assert row["source_review"] == "original_pdf_visual"
    assert row["completeness"] == "statistiche_essenziali"
    assert row["ability_scores"] == {
        "for": 16, "des": 8, "cos": 14, "int": 6, "sag": 10, "car": 3,
    }
    m = re.fullmatch(r"(\d+) \((\d+)d(4|6|8|10|12|20) \+ (\d+)\)", row["hit_points"])
    assert m is not None
    hp, n, die, bonus = map(int, m.groups())
    assert math.floor(n * (die + 1) / 2) + bonus == hp == 26
