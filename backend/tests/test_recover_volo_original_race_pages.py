"""Synthetic safety checks for Volo original printed-versus-physical pages."""

from scripts.recover_volo_original_race_pages import (
    SOURCE, TARGETS, WINDOW_MAX, page_score, valid_row,
)


def test_sixteen_rows_and_bounded_ocr_windows():
    assert len(TARGETS) == 16
    assert len({t[0] for t in TARGETS}) == len(TARGETS)
    assert WINDOW_MAX == 12
    assert all(104 <= t[1] <= 120 for t in TARGETS)


def test_edition_specific_traits_and_original_name_required():
    t = TARGETS[7]
    sample = (
        f"{t[2]}: An invented race rule.\n"
        + "\n".join(f"{label}. Imaginary mechanics." for label in t[3])
        + "\n" + "A fictional testing page only. " * 30
    )
    report = page_score(sample, t)
    assert report["sufficient"]
    assert report["feature_count"] == len(t[3])
    assert "Imaginary" not in repr(report)
    assert not page_score("Lizardfolk ... table of contents" + " " * 2000, t)["sufficient"]


def test_protector_uses_unique_trait_as_gating_feature():
    target = TARGETS[2]
    okay = ("Protector Aasimar\nRadiant Soul\n" + "Fictional example. " * 70)
    assert page_score(okay, target)["sufficient"]
    wrong = ("Scourge Aasimar\nRadiant Consumption\n" + "Fictional example. " * 70)
    assert not page_score(wrong, target)["sufficient"]


def test_only_pending_records_with_matching_printed_page_are_eligible():
    target = TARGETS[1]
    item = {"target": target}
    row = {
        "name": target[0], "source_key": SOURCE, "reference_type": "subrace",
        "review_status": "verified", "ai_review_status": "pending",
        "source_full_text": "", "source_text_checksum": "",
        "source_refs": [{"filename": SOURCE, "page": target[1]}],
    }
    assert valid_row(row, item)
    assert not valid_row({**row, "ai_review_status": "verified"}, item)
    assert not valid_row({**row, "source_text_checksum": "existing"}, item)
    assert not valid_row({**row, "source_key": "bad.pdf"}, item)
    assert not valid_row({**row, "source_refs": []}, item)


def test_old_legacy_rule_without_heading_does_not_pass():
    target = TARGETS[-1]
    unrelated = ("Magic Resistance. Poison Immunity. " * 70)
    assert not page_score(unrelated, target)["sufficient"]
