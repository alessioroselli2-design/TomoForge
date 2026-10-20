"""Tests for independent Van Richten 12-page windows and duplicate prevention."""
from copy import deepcopy

import pytest
from scripts import vrgr_r2_window_plan as p


def fake_report(start: int, end: int) -> dict:
    return {
        "logical_source_id": p.SOURCE_ID,
        "source_sha256_matched": True,
        "database_writes": 0,
        "status": p.EXPECTED_STATUS,
        "start_page": start, "end_page": end,
        "quality_pass_pages": list(range(start, end + 1)),
        "quality_failed_pages": [],
        "independently_agreed_candidates": 0,
        "blocked_invalid_hit_dice": [],
        "candidates_for_manual_review": [],
    }


def sample_candidate(name: str, page: int) -> dict:
    return {
        "name": name, "physical_page": page,
        "core_fields": {
            "classe_armatura": "14", "punti_ferita": "9 (2d8)", "velocita": "9 m"
        },
        "independent_ocr_agreement": True,
        "manual_review_required": True,
    }


def test_all_windows_are_bounded_disjoint_and_cover_p177_to_p257():
    p.validate_windows()
    assert len(p.WINDOWS) == 6
    assert max(e - s + 1 for s, e in p.WINDOWS) <= 12
    pages = {page for s, e in p.WINDOWS for page in range(s, e + 1)}
    assert len(pages) == 69
    assert pages | set(range(201, 213)) == set(range(177, 258))


def test_empty_survey_cannot_authorize_import():
    summary = p.combine_readonly_reports([fake_report(s, e) for s, e in p.WINDOWS])
    assert summary["pages_quality_pass"] == 69
    assert summary["ready_for_canonical_import"] is False
    assert summary["any_database_writes"] == 0


def test_same_name_in_two_windows_is_blocked():
    reports = [fake_report(s, e) for s, e in p.WINDOWS]
    reports[0]["candidates_for_manual_review"] = [sample_candidate("Vampiro", 177)]
    reports[2]["candidates_for_manual_review"] = [sample_candidate("VAMPIRO", 213)]
    summary = p.combine_readonly_reports(reports)
    assert not summary["source_candidate_names"]
    assert summary["cross_window_duplicate_names_blocked"] == ["vampiro"]


def test_wrong_source_page_and_unauthorized_text_fail_closed():
    reports = [fake_report(s, e) for s, e in p.WINDOWS]
    reports[0]["candidates_for_manual_review"] = [sample_candidate("Nuovo Mostro", 211)]
    with pytest.raises(ValueError, match="candidate_provenance_or_field_gate"):
        p.combine_readonly_reports(reports)
    reports = [fake_report(s, e) for s, e in p.WINDOWS]
    candidate = sample_candidate("Nuovo Mostro", 177)
    candidate["private_ocr"] = "not allowed"
    reports[0]["candidates_for_manual_review"] = [candidate]
    with pytest.raises(ValueError, match="candidate_provenance_or_field_gate"):
        p.combine_readonly_reports(reports)


def test_mutation_of_database_writes_fails():
    reports = [fake_report(s, e) for s, e in p.WINDOWS]
    modified = deepcopy(reports)
    modified[0]["database_writes"] = 1
    with pytest.raises(ValueError, match="untrusted_or_misplaced_window_report"):
        p.combine_readonly_reports(modified)
