"""Synthetic, source-free tests for read-only race page discovery."""

from scripts.verdan_wildemount_race_pages import PAGE_LIMIT, SOURCES, page_facts


def test_window_limit():
    assert PAGE_LIMIT == 12
    assert len(SOURCES) == 2


def test_verdan_rule_markers_and_name():
    text = (
        "Verdan\nAbility Score Increase. A fictional mechanic.\n"
        "Size. Small.\nSpeed. Printed.\nLanguages. Printed."
    )
    facts = page_facts(text, SOURCES[0]["names"])
    assert facts["mentioned_race_keys"] == ["verdan"]
    assert facts["rule_markers"]["ability_scores"]
    assert facts["rule_markers"]["speed"]
    assert "fictional mechanic" not in str(facts)


def test_wildemount_naming_variations():
    sample = "Pallid Elves and the Lotusden Halfling dwell nearby."
    facts = page_facts(sample, SOURCES[1]["names"])
    assert "pallid elves" in facts["mentioned_race_keys"]
    assert "lotusden halfling" in facts["mentioned_race_keys"]
    assert not facts["rule_markers"]["ability_scores"]


def test_unrelated_story_page_has_no_name_candidate():
    facts = page_facts("A merchant and a caravan cross the country.", SOURCES[1]["names"])
    assert facts["mentioned_race_keys"] == []
