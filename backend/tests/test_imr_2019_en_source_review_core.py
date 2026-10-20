"""Fail-closed source-locked review of 81 Infernal Machine Rebuild statblocks."""
import json
import math
import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "data" / "imr_2019_en_source_review_core.json"
SHA = "880abee59beac3f284de966a3bd1c6270e3bb90b6d11d0e164e57f9056241f6a"
DICE = re.compile(r"^(\d+) \((\d+)d(4|6|8|10|12|20)(?: ([+-]) (\d+))?\)$")
ABILITY_KEYS = {"for", "des", "cos", "int", "sag", "car"}


def test_source_identity_and_closed_scope():
    d = json.loads(DOC.read_text(encoding="utf-8"))
    assert d["authority"]["logical_source_id"] == "imr_2019_en"
    assert d["authority"]["sha256"] == SHA
    assert d["authority"]["physical_pdf_pages"] == 111
    assert d["audit"]["all_pdf_pages_reviewed"] == 111
    assert d["audit"]["distinct_statblocks"] == 81
    assert d["audit"]["new_candidate_identities"] == 20
    assert d["audit"]["existing_canonical_identities"] == 61
    assert d["audit"]["missing_source_cr_count"] == 1
    assert d["audit"]["db_writes"] == 0
    assert d["audit"]["full_actions_spells_traits_complete"] is False
    assert d["audit"]["original_pdf_raw_ocr_not_committed"] is True


def test_mechanical_data_complete_and_all_hit_dice_coherent():
    records = json.loads(DOC.read_text(encoding="utf-8"))["statblocks"]
    assert len(records) == 81
    assert len({r["name"].casefold() for r in records}) == 81
    for r in records:
        assert 52 <= r["physical_pdf_page"] <= 93
        assert r["source_review"] == "original_pdf_text_layout"
        assert r["completeness"] == "statistiche_essenziali"
        assert r["size_and_type"] and r["speed"] and r["armor_class"]
        assert set(r["ability_scores"]) == ABILITY_KEYS
        assert all(1 <= v <= 30 for v in r["ability_scores"].values())
        match = DICE.fullmatch(r["hit_points"])
        assert match, r["name"]
        hp, count, sides, sign, modifier = match.groups()
        mean = math.floor(int(count) * (int(sides) + 1) / 2)
        mean += (-1 if sign == "-" else 1) * int(modifier or 0)
        assert mean == int(hp), r["name"]
        if r["challenge_rating"] is not None:
            assert re.fullmatch(r"(0|[1-9]\d*)(/[1-9]\d*)?", r["challenge_rating"])


def test_canons_and_named_variants():
    records = json.loads(DOC.read_text(encoding="utf-8"))["statblocks"]
    assert sum(r["import_decision"] == "candidate_new" for r in records) == 20
    assert sum(r["import_decision"] == "link_existing_identity" for r in records) == 61
    by_name = {r["name"]: r for r in records}
    assert by_name["Sacred Statue"]["challenge_rating"] is None
    assert by_name["Sacred Statue"]["existing_canonical_name"] == "Statua Sacra"
    assert by_name["The Demogorgon"]["identity_disambiguation"].startswith("Named ettin")
    assert by_name["Thessalkraken"]["existing_canonical_name"] is None
    assert by_name["Redcap"]["possible_source_variant"]
    assert by_name["Brain in a Jar"]["existing_canonical_name"] == "Cervello in Barattolo"
