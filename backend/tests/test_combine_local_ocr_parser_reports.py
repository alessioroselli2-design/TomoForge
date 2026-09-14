from scripts.combine_local_ocr_parser_reports import combine_reports


def _report(start: int, end: int, agreed: int, guided: int) -> dict:
    return {
        "filename": "private-manual.pdf",
        "r2_key": "private-manual.pdf",
        "size_bytes": 123,
        "start_page": start,
        "end_page": end,
        "page_count_requested": 12,
        "pages_read": 12,
        "quality_pages_passed": 12,
        "quality_pages_evaluated": 12,
        "records_detected": 10,
        "records_flagged_for_review": 10,
        "records_with_ocr_review_flag": 10,
        "source_pages_represented": 12,
        "record_types": {"monster": 2, "weapon": 8},
        "monster_candidates_primary": 2,
        "monster_candidates_comparison": 3,
        "monster_candidates_independently_agreed": agreed,
        "monster_candidates_guided_core_merged": guided,
        "monster_primary_with_same_page_containment_name_candidate": 1,
        "page_quality": [
            {"page": start, "quality_pass": True},
            {"page": end, "quality_pass": True},
        ],
    }


def test_combine_reports_sums_only_aggregate_counts_across_bounded_windows():
    combined = combine_reports([
        _report(12, 23, agreed=1, guided=1),
        _report(24, 35, agreed=2, guided=1),
    ])

    assert combined["sample_mode"] == "bounded_multi_window"
    assert combined["start_page"] == 12
    assert combined["end_page"] == 35
    assert combined["page_count_requested_total"] == 24
    assert combined["window_count"] == 2
    assert combined["quality_pages_passed"] == 24
    assert combined["quality_pages_evaluated"] == 24
    assert combined["records_detected"] == 20
    assert combined["record_types"] == {"monster": 4, "weapon": 16}
    assert combined["monster_candidates_primary"] == 4
    assert combined["monster_candidates_comparison"] == 6
    assert combined["monster_candidates_independently_agreed"] == 3
    assert combined["monster_candidates_guided_core_merged"] == 2
    assert combined["monster_primary_with_same_page_containment_name_candidate"] == 2
    assert [item["page"] for item in combined["page_quality"]] == [12, 23, 24, 35]
    assert combined["windows"][0]["monster_candidates_guided_core_merged"] == 1
    assert combined["windows"][1]["monster_candidates_independently_agreed"] == 2


def test_combine_reports_rejects_mixed_sources():
    left = _report(12, 23, agreed=1, guided=1)
    right = _report(24, 35, agreed=0, guided=0)
    right["filename"] = "another-manual.pdf"

    try:
        combine_reports([left, right])
    except ValueError as exc:
        assert "same filename" in str(exc)
    else:
        raise AssertionError("mixed source reports must fail closed")
