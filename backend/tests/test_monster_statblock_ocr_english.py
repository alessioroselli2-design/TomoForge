from pathlib import Path
import sys

SERVICES = Path(__file__).resolve().parents[1] / "services"
if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from monster_statblock_ocr import agreed_monster_records, parse_monster_statblocks


def _english_goblin(ac="15 (leather armor, shield)", title="SPACE GOBLIN"):
    return f"""{title}
Small humanoid (goblinoid), neutral evil
Armor Class {ac}
Hit Points 7 (2d6)
Speed 30 ft.
STR DEX CON INT WIS CHA
8 14 10 10 8 8
Saving Throws Dex +4
Skills Stealth +6
Senses darkvision 60 ft., passive Perception 9
Languages Common, Goblin
Challenge 1/4 (50 XP)
Proficiency Bonus +2

Actions
Scimitar. Melee Weapon Attack: +4 to hit.
"""


def test_parses_english_statblock_into_canonical_italian_attribute_keys():
    records = parse_monster_statblocks(
        [(12, _english_goblin())],
        "boos-astral-menagerie.pdf",
        "en",
    )

    assert len(records) == 1
    record = records[0]
    assert record["reference_type"] == "monster"
    assert record["source_refs"] == [
        {
            "filename": "boos-astral-menagerie.pdf",
            "page": 12,
            "logical_page": 12,
            "language": "en",
        }
    ]

    attributes = record["attributes"]
    assert attributes["classe_armatura"].startswith("15")
    assert attributes["punti_ferita"].startswith("7")
    assert attributes["velocita"].startswith("30 ft")
    assert attributes["grado_sfida"].startswith("1/4")
    assert attributes["tiri_salvezza"] == "Dex +4"
    assert attributes["abilita"] == "Stealth +6"
    assert attributes["caratteristiche"] == {
        "for": "8",
        "des": "14",
        "cos": "10",
        "int": "10",
        "sag": "8",
        "car": "8",
    }
    assert attributes["ha_azioni"] is True

    # English labels are input aliases only; persistable attributes keep the
    # existing canonical Italian schema.
    for forbidden in ("armor_class", "hit_points", "speed", "challenge"):
        assert forbidden not in attributes

    assert "ocr_da_verificare" in record["review_flags"]


def test_english_statblock_missing_one_core_field_fails_closed():
    text = _english_goblin().replace("Hit Points 7 (2d6)\n", "")
    assert parse_monster_statblocks([(12, text)], "boos.pdf", "en") == []


def test_english_statblock_still_requires_independent_core_agreement():
    primary = parse_monster_statblocks([(12, _english_goblin())], "boos.pdf", "en")
    same = parse_monster_statblocks([(12, _english_goblin())], "boos.pdf", "en")
    different_ac = parse_monster_statblocks(
        [(12, _english_goblin("14 (leather armor)"))],
        "boos.pdf",
        "en",
    )

    agreed = agreed_monster_records(primary, same)
    assert len(agreed) == 1
    assert agreed[0]["attributes"]["ocr_independent_agreement"] is True
    assert "ocr_da_verificare" in agreed[0]["review_flags"]

    assert agreed_monster_records(primary, different_ac) == []


def test_english_descriptor_and_structural_headings_are_not_misread_as_titles():
    text = """Armor Class
Small humanoid
Hit Points 7 (2d6)
Speed 30 ft.
"""
    assert parse_monster_statblocks([(12, text)], "boos.pdf", "en") == []
