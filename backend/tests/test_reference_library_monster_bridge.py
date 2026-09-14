from pathlib import Path

import pymupdf as fitz

import reference_library as library


ENGLISH_MONSTER = """ASTRAL STALKER
Medium aberration, neutral evil
Armor Class 15 (natural armor)
Hit Points 68 (8d8 + 32)
Speed 30 ft., fly 40 ft.
STR DEX CON INT WIS CHA
16 14 18 11 13 8
Saving Throws Dex +5, Con +7
Skills Perception +4
Senses darkvision 60 ft., passive Perception 14
Languages Common, Deep Speech
Challenge 5 (1,800 XP)
Proficiency Bonus +3
Actions
Multiattack. The astral stalker makes two attacks.
Claw. Melee Weapon Attack: +6 to hit, reach 5 ft., one target.
"""


def _blank_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "english-monsters.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    return path


def test_english_ocr_other_is_promoted_to_review_monster(tmp_path):
    path = _blank_pdf(tmp_path)

    report = library.extract_reference_records(
        path,
        ocr_page=lambda _page, _page_number: ENGLISH_MONSTER,
        start_page=1,
        end_page=1,
        force_ocr=True,
        source_language="en",
    )

    matches = [
        record
        for record in report.records
        if record.get("normalized_name") == "astral stalker"
    ]
    assert len(matches) == 1
    record = matches[0]

    assert record["reference_type"] == "monster"
    assert record["attributes"]["classe_armatura"].startswith("15")
    assert record["attributes"]["punti_ferita"].startswith("68")
    assert record["attributes"]["velocita"].startswith("30 ft")
    assert record["attributes"]["grado_sfida"].startswith("5")
    assert record["attributes"]["caratteristiche"] == {
        "for": "16",
        "des": "14",
        "cos": "18",
        "int": "11",
        "sag": "13",
        "car": "8",
    }
    assert "armor_class" not in record["attributes"]
    assert "hit_points" not in record["attributes"]
    assert "speed" not in record["attributes"]
    assert "challenge" not in record["attributes"]
    assert "ocr_da_verificare" in record["review_flags"]
    assert library.reference_review_state(record) == "review"
    assert record["source_refs"][0]["filename"] == "english-monsters.pdf"
    assert record["source_refs"][0]["page"] == 1


def test_missing_core_field_stays_other(tmp_path):
    path = _blank_pdf(tmp_path)
    incomplete = ENGLISH_MONSTER.replace("Speed 30 ft., fly 40 ft.\n", "")

    report = library.extract_reference_records(
        path,
        ocr_page=lambda _page, _page_number: incomplete,
        start_page=1,
        end_page=1,
        force_ocr=True,
        source_language="en",
    )

    matches = [
        record
        for record in report.records
        if record.get("normalized_name") == "astral stalker"
    ]
    assert len(matches) == 1
    assert matches[0]["reference_type"] == "other"
    assert "ocr_da_verificare" in matches[0]["review_flags"]


def test_non_english_ocr_is_not_reclassified_by_bridge():
    record = {
        "id": "ref_other",
        "reference_type": "other",
        "name": "ASTRAL STALKER",
        "normalized_name": "astral stalker",
        "description": "generic",
        "full_text": "generic",
        "attributes": {},
        "tags": [],
        "source_refs": [{"filename": "manual.pdf", "page": 1}],
        "review_flags": ["ocr_da_verificare"],
    }

    result = library._promote_ocr_english_monsters(
        [record],
        ENGLISH_MONSTER,
        "manual.pdf",
        1,
        "it",
    )

    assert result[0]["reference_type"] == "other"
