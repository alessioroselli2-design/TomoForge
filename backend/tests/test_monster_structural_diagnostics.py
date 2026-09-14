from services.monster_structural_diagnostics import english_monster_structural_diagnostics


def test_english_statblock_signals_are_aggregate_only():
    text = """ASTRAL CREATURE
Large aberration
Armor Class 15
Hit Points 45 (6d10+12)
Speed 30 ft., fly 40 ft.
STR DEX CON INT WIS CHA
16 14 14 10 12 8
Saving Throws Dex +4
Senses darkvision 60 ft.
Languages Common
Challenge 3
Proficiency Bonus +2
Actions
Multiattack
Wildspace creature using an air envelope.
"""
    records = [
        {
            "reference_type": "other",
            "full_text": text,
            "source_refs": [{"page": 12}],
            "name": "Private monster name",
        }
    ]

    summary = english_monster_structural_diagnostics([(12, text)], records)

    assert summary["boos_structural_pages_evaluated"] == 1
    assert summary["boos_structural_pages_with_english_core_pair"] == 1
    assert summary["boos_structural_pages_with_english_core_triplet"] == 1
    assert summary["boos_structural_pages_with_ability_header"] == 1
    assert summary["boos_structural_pages_with_challenge_or_proficiency"] == 1
    assert summary["boos_structural_pages_with_actions_heading"] == 1
    assert summary["boos_structural_pages_with_spelljammer_context"] == 1
    assert summary["boos_structural_pages_with_monster_like_bundle"] == 1
    assert summary["boos_structural_other_records_with_english_core_pair"] == 1
    assert summary["boos_structural_other_records_with_english_core_triplet"] == 1
    assert summary["boos_structural_other_records_with_monster_like_bundle"] == 1
    assert summary["boos_structural_other_records_on_monster_like_pages"] == 1
    assert summary["boos_structural_monster_records_on_monster_like_pages"] == 0
    assert all(isinstance(value, int) for value in summary.values())
    serialized = str(summary)
    assert "Private monster name" not in serialized
    assert "Multiattack" not in serialized
    assert "air envelope" not in serialized


def test_narrative_page_does_not_look_like_statblock():
    text = "A voyage through the Astral Sea describes spelljammers and distant Wildspace systems."
    records = [
        {
            "reference_type": "other",
            "full_text": text,
            "source_refs": [{"page": 13}],
        }
    ]

    summary = english_monster_structural_diagnostics([(13, text)], records)

    assert summary["boos_structural_pages_with_spelljammer_context"] == 1
    assert summary["boos_structural_pages_with_english_core_pair"] == 0
    assert summary["boos_structural_pages_with_monster_like_bundle"] == 0
    assert summary["boos_structural_other_records_with_monster_like_bundle"] == 0
