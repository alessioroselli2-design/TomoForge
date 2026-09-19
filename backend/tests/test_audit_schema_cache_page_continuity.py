from scripts.audit_schema_cache_page_continuity import (
    summarize_schema_cache_page_continuity,
)


def _job(**overrides):
    job = {
        "status": "failed",
        "last_error": "PGRST204 schema cache",
        "records_imported": 2,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "current_page": 3,
        "page_count": 6,
        "filename": "Manuale_1700000000000.pdf",
    }
    job.update(overrides)
    return job


def _record(page):
    return {
        "id": f"r{page}",
        "source_refs": [{"filename": "Manuale.pdf", "page": page}],
    }


def test_final_page_reference_does_not_hide_internal_gaps():
    result = summarize_schema_cache_page_continuity(
        [_job()],
        [_record(1), _record(3), _record(4), _record(6)],
    )

    assert result["schema_cache_failures_with_progress_gap"] == 1
    assert result["nominal_missing_pages"] == 3
    assert result["observed_pages_in_declared_range"] == 4
    assert result["observed_pages_after_progress"] == 2
    assert result["missing_pages_through_reported_progress"] == 1
    assert result["missing_pages_after_reported_progress"] == 1
    assert result["jobs_contiguous_through_reported_progress"] == 0
    assert result["jobs_fully_covered_after_reported_progress"] == 0
    assert result["record_set_completeness_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_continuous_refs_are_measured_without_confirming_completeness():
    result = summarize_schema_cache_page_continuity(
        [_job()],
        [_record(page) for page in range(1, 7)],
    )

    assert result["missing_pages_through_reported_progress"] == 0
    assert result["missing_pages_after_reported_progress"] == 0
    assert result["jobs_contiguous_through_reported_progress"] == 1
    assert result["jobs_fully_covered_after_reported_progress"] == 1
    assert result["record_set_completeness_confirmed"] is False


def test_out_of_range_and_invalid_pages_do_not_count_as_coverage():
    records = [
        _record(0),
        _record(7),
        {"id": "bad", "source_refs": [{"filename": "Manuale.pdf", "page": True}]},
    ]

    result = summarize_schema_cache_page_continuity([_job()], records)

    assert result["observed_pages_in_declared_range"] == 0
    assert result["missing_pages_through_reported_progress"] == 3
    assert result["missing_pages_after_reported_progress"] == 3


def test_completed_or_page_complete_jobs_are_out_of_scope():
    result = summarize_schema_cache_page_continuity(
        [_job(status="completed"), _job(current_page=6)],
        [],
    )

    assert result["schema_cache_failures_with_progress_gap"] == 0
    assert result["nominal_missing_pages"] == 0
