"""Synthetic, private-text-free Theros and Locathah source gate tests."""

from scripts.theros_locathah_source_audit import (
    MAX_WINDOW,
    SOURCES,
    structural_signals,
)


def test_source_windows_are_independently_bounded():
    assert MAX_WINDOW == 12
    for src in SOURCES:
        assert 1 <= src["last"] - src["first"] + 1 <= MAX_WINDOW


def test_leonin_page_facts_without_reproducing_rules():
    fake = (
        "LEONIN\n"
        "Ability Score Increase. Sample score change.\n"
        "Size. Medium.\n"
        "Speed. A nonzero walking speed.\n"
        "Darkvision. The text defines a vision radius."
    )
    value = structural_signals(fake, ("Leonin", "Satyr"))
    assert value["mentions"] == ["Leonin"]
    assert value["heading_candidates"] == ["Leonin"]
    assert value["markers"]["score_bonus"]
    assert value["markers"]["speed"]
    assert fake not in str(value)


def test_unrelated_story_text_does_not_imply_racial_rules():
    value = structural_signals(
        "Satyrs gather at the town. A Leonin wandered far from home.",
        ("Leonin", "Satyr"),
    )
    assert not value["heading_candidates"]
    assert not any(value["markers"].values())


def test_locathah_structural_detection():
    value = structural_signals(
        "LOCATHAH\n"
        "Ability Score Increase. Fictional modifier.\n"
        "Natural Armor. Fictional effect.\n"
        "Languages. Aquan and Common.",
        ("Locathah",),
    )
    assert value["heading_candidates"] == ["Locathah"]
    assert value["markers"]["natural_armor"]
    assert value["markers"]["languages"]
