"""All fixtures synthetic: do not upload text from licensed manuals."""

from scripts.legacy_races_r2_audit import SOURCES, WINDOW_MAX, short_evidence


def test_each_source_window_is_bounded():
    assert len(SOURCES) == 3
    assert WINDOW_MAX == 12
    assert all(1 <= s["end"] - s["start"] + 1 <= WINDOW_MAX for s in SOURCES)


def test_tiefling_legacy_candidate_keeps_only_metadata():
    sample = (
        "Baalzebul\nAbility Score Increase. Fictional score.\n"
        "Legacy of Maladomini. An imaginary sentence.\n"
        "Languages. Two invented languages.\n"
    )
    result = short_evidence(sample, SOURCES[0]["names"])
    assert result["candidate_mentions"] == ["Baalzebul"]
    assert result["number_of_rule_anchors"] >= 2
    assert "imaginary" not in repr(result)


def test_index_title_without_rules_is_not_complete():
    result = short_evidence("Zariel, Levistus, Dispater", SOURCES[0]["names"])
    assert result["candidate_mentions"] == ["Dispater", "Levistus", "Zariel"]
    assert result["number_of_rule_anchors"] == 0


def test_other_source_name_not_promoted():
    result = short_evidence("This chapter is about Tortle.", SOURCES[0]["names"])
    assert result["candidate_mentions"] == []
