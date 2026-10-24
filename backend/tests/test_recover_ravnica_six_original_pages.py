"""Source-only synthetic Ravnica tests; never embed copyrighted text."""

from scripts.recover_ravnica_six_original_pages import (
    SOURCE, DB_SOURCE, HASH, TARGETS, WINDOW_MAX, page_score, valid_row,
)


def test_six_distinct_playable_races_and_bounded_windows():
    assert len(TARGETS) == 6
    assert len({t[0] for t in TARGETS}) == 6
    assert WINDOW_MAX == 12
    assert all(16 <= t[1] <= 22 for t in TARGETS)


def test_race_heading_requires_independent_published_traits():
    target = TARGETS[4]
    fictional = (
        target[2] + "\n"
        + "\n".join(target[3])
        + "\n" + ("Synthetic sample only. " * 70)
    )
    assert page_score(fictional, target)["sufficient"]
    assert not page_score("Simic Hybrid menu\n" + "Example menu. " * 100, target)["sufficient"]


def test_correct_logical_to_physical_source_fingerprint():
    target = TARGETS[0]
    item = {"target": target}
    row = {
        "name": target[0],
        "reference_type": "race",
        "source_key": DB_SOURCE,
        "review_status": "verified",
        "ai_review_status": "pending",
        "source_full_text": "", "source_text_checksum": "",
        "source_refs": [{
            "filename": SOURCE, "page": target[1],
            "source_sha256": HASH, "logical_source_id": "ggtr_2018_en",
        }],
    }
    assert valid_row(row, item)
    assert not valid_row({**row, "source_key": SOURCE}, item)
    assert not valid_row({**row, "source_text_checksum": "prior"}, item)
    assert not valid_row({**row, "ai_review_status": "verified"}, item)
    assert not valid_row({**row, "source_refs": [{
        **row["source_refs"][0], "source_sha256": "changed"
    }]}, item)
