"""Contract tests for the metadata-only, read-only R2 race scan."""

import json

from scripts.races_r2_native_audit import MAX_WINDOW, page_candidates

RAVNICA = "Guildmasters’ Guide to Ravnica.2 .pdf"
SYNTHETIC_RULES = (
    "Ability Score Increase. A character changes their ability scores.\n"
    "Size. The character is Medium; refer to this playable race's size rule.\n"
    "Speed. The character has the walking speed in their species traits.\n"
    "Languages. The character knows languages defined by these playable rules."
)


def test_positive_candidate_is_metadata_only_and_requires_review():
    text = f"Loxodon\n{SYNTHETIC_RULES}"
    result = page_candidates(text, RAVNICA, 22, "en")
    assert result == [
        {"name": "Loxodon", "normalized_name": "loxodon", "page": 22, "review_required": True}
    ]
    assert SYNTHETIC_RULES not in json.dumps(result)


def test_page_heading_without_rules_is_not_promoted():
    result = page_candidates(
        "Loxodon\nA heading in an alphabetical table of contents; "
        "no playable creature mechanics are given in this section. "
        "This index merely mentions a name and background locations.",
        RAVNICA,
        2,
        "en",
    )
    assert result == []


def test_wrong_manual_cannot_generate_candidate():
    assert page_candidates(f"Loxodon\n{SYNTHETIC_RULES}", "Unrelated.pdf", 22, "en") == []


def test_windows_cannot_exceed_twelve_pages():
    assert MAX_WINDOW == 12
