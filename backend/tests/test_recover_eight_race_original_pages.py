"""Synthetic tests for bounded multi-manual original source recovery."""

from scripts.recover_eight_race_original_pages import (
    SOURCES, accepted, check_text, valid_old_record,
)


def test_source_window_and_unique_targets():
    assert len(SOURCES) == 5
    targets = [(s, t) for s in SOURCES for t in s["targets"]]
    assert len(targets) == 8
    assert len({t[0] for _, t in targets}) == 8
    assert all(len(s["sha"]) == 64 for s in SOURCES)
    assert all(1 <= t[3] <= s["pages"] for s, t in targets)


def test_two_source_modes_must_contain_heading_and_distinct_rules():
    source, target = SOURCES[0], SOURCES[0]["targets"][0]
    good = target[2] + "\n" + "\n".join(target[4]) + "\n" + "Fictional test. " * 75
    assert accepted(good, good, target)
    assert check_text(good, target)["feature_matches"] == 3
    incomplete = target[2] + " Shell Defense\n" + "Fictional test. " * 75
    assert not accepted(good, incomplete, target)
    assert "Fictional" not in str(check_text(good, target))


def test_fizban_race_headings_are_not_interchangeable():
    source = SOURCES[-1]
    chromatic = source["targets"][0]
    metallic = source["targets"][2]
    text = "Dragonide Cromatico Taglia Velocità Soffio " + "Fictional. " * 95
    assert accepted(text, text, chromatic)
    assert not accepted(text, text, metallic)


def test_existing_or_other_manual_record_is_never_overwritten():
    src = SOURCES[1]
    target = src["targets"][0]
    item = {"target": target, "source": src["filename"]}
    row = {
        "id": target[0], "name": target[1], "source_key": src["filename"],
        "reference_type": "race", "review_status": "verified",
        "ai_review_status": "pending", "source_full_text": "",
        "source_text_checksum": "",
        "source_refs": [{"filename": src["filename"], "page": target[3]}],
    }
    assert valid_old_record(row, item)
    assert not valid_old_record({**row, "ai_review_status": "verified"}, item)
    assert not valid_old_record({**row, "source_text_checksum": "existing"}, item)
    assert not valid_old_record({**row, "source_refs": []}, item)
    assert not valid_old_record({**row, "source_key": "other.pdf"}, item)
