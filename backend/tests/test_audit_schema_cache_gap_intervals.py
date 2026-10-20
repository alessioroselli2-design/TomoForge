from scripts.audit_schema_cache_gap_intervals import (
    _contiguous_intervals,
    summarize_schema_cache_gap_intervals,
)


def _job(**overrides):
    job = {
        "status": "failed",
        "last_error": "PGRST204 schema cache",
        "records_imported": 2,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "current_page": 4,
        "page_count": 10,
        "filename": "Manuale_1700000000000.pdf",
    }
    job.update(overrides)
    return job


def _record(page):
    return {
        "id": f"r{page}",
        "source_refs": [{"filename": "Manuale.pdf", "page": page}],
    }


def test_contiguous_intervals_groups_isolated_and_ranges():
    assert _contiguous_intervals([1, 3, 4, 5, 8, 8]) == [(1, 1), (3, 5), (8, 8)]
    assert _contiguous_intervals([]) == []


def test_gap_audit_distinguishes_isolated_pages_from_contiguous_ranges():
    result = summarize_schema_cache_gap_intervals(
        [_job()],
        [_record(page) for page in (1, 3, 4, 5, 8, 10)],
    )

    # Missing through progress: page 2. Missing after progress: 6-7 and 9.
    assert result["missing_pages_total"] == 4
    assert result["missing_gap_intervals_total"] == 3
    assert result["isolated_missing_pages_total"] == 2
    assert result["contiguous_gap_intervals_total"] == 1
    assert result["pages_in_contiguous_gaps_total"] == 2
    assert result["longest_gap_pages"] == 2
    assert result["missing_pages_through_reported_progress"] == 1
    assert result["gap_intervals_through_reported_progress"] == 1
    assert result["longest_gap_through_reported_progress"] == 1
    assert result["missing_pages_after_reported_progress"] == 3
    assert result["gap_intervals_after_reported_progress"] == 2
    assert result["longest_gap_after_reported_progress"] == 2
    assert result["jobs_with_contiguous_gaps"] == 1
    assert result["jobs_with_only_isolated_gaps"] == 0


def test_only_isolated_gaps_do_not_look_like_contiguous_missing_ranges():
    result = summarize_schema_cache_gap_intervals(
        [_job(current_page=3, page_count=6)],
        [_record(page) for page in (1, 3, 4, 6)],
    )

    assert result["missing_pages_total"] == 2
    assert result["isolated_missing_pages_total"] == 2
    assert result["contiguous_gap_intervals_total"] == 0
    assert result["jobs_with_contiguous_gaps"] == 0
    assert result["jobs_with_only_isolated_gaps"] == 1


def test_complete_coverage_has_no_gap_intervals_but_never_confirms_completeness():
    result = summarize_schema_cache_gap_intervals(
        [_job()],
        [_record(page) for page in range(1, 11)],
    )

    assert result["missing_pages_total"] == 0
    assert result["missing_gap_intervals_total"] == 0
    assert result["longest_gap_pages"] == 0
    assert result["record_set_completeness_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_jobs_without_a_schema_cache_progress_gap_are_excluded():
    result = summarize_schema_cache_gap_intervals(
        [_job(status="completed"), _job(current_page=10)],
        [],
    )

    assert result["schema_cache_failures_with_progress_gap"] == 0
    assert result["missing_pages_total"] == 0
