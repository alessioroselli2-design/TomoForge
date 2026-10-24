"""Synthetic tests for five pending private source-page recoveries."""
from scripts.recover_five_race_source_pages import accepted, valid_old_record
from scripts.recover_next_five_race_source_pages import SOURCES


def _fake_text(target):
    return (
        target[2] + "\n" +
        "\n".join(f"{name}. Invented testing material." for name in target[4]) +
        "\n" + ("Synthetic content with no manual text. " * 30)
    )


def test_five_distinct_targets_and_one_page_windows():
    targets = [t for config in SOURCES for t in config["targets"]]
    assert len(targets) == len({t[0] for t in targets}) == 5
    assert all(len(config["sha"]) == 64 for config in SOURCES)
    assert all(t[3] > 0 for t in targets)


def test_independent_text_modes_required_for_each():
    for config in SOURCES:
        for target in config["targets"]:
            complete = _fake_text(target)
            assert accepted(complete, complete, target)
            incomplete = target[2] + "\n" + ("Synthetic content. " * 80)
            assert not accepted(complete, incomplete, target)


def test_pending_only_and_original_source_fingerprint():
    for config in SOURCES:
        for target in config["targets"]:
            evidence = {"target": target, "source": config["filename"]}
            row = {
                "id": target[0],
                "name": target[1],
                "source_key": config["filename"],
                "reference_type": "race",
                "review_status": "verified",
                "ai_review_status": "pending",
                "source_full_text": "",
                "source_text_checksum": "",
                "source_refs": [{"filename": config["filename"], "page": target[3]}],
            }
            assert valid_old_record(row, evidence)
            assert not valid_old_record({**row, "ai_review_status": "verified"}, evidence)
            assert not valid_old_record({**row, "source_full_text": "existing original"}, evidence)
            assert not valid_old_record({**row, "source_refs": []}, evidence)
