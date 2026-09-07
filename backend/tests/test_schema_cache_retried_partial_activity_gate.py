from scripts.audit_schema_cache_partial_activity import summarize_schema_cache_partial_activity


def test_retried_schema_cache_failures_with_partial_activity_remain_review_only():
    jobs = [
        {
            "status": "failed",
            "last_error": "PGRST204: field missing from schema cache",
            "records_updated": 87,
            "records_flagged": 54,
            "pages_needing_ocr": [],
            "attempt_count": 2,
        },
        {
            "status": "failed",
            "last_error": "PGRST204: field missing from schema cache",
            "records_imported": 34,
            "records_updated": 57,
            "records_flagged": 32,
            "pages_needing_ocr": [],
            "attempt_count": 2,
        },
    ]

    result = summarize_schema_cache_partial_activity(jobs)

    assert result["failed_schema_cache_jobs"] == 2
    assert result["failed_schema_cache_jobs_with_record_activity"] == 2
    assert result["failed_schema_cache_jobs_with_activity_without_ocr"] == 2
    assert result["failed_schema_cache_jobs_with_activity_retried"] == 2
    assert result["failed_schema_cache_jobs_for_read_only_reconciliation"] == 2
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
