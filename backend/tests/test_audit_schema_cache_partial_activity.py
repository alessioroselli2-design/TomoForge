from scripts.audit_schema_cache_partial_activity import summarize_schema_cache_partial_activity


def test_schema_cache_partial_activity_is_read_only_and_private():
    private_error = "PGRST204 schema cache private payload"
    jobs = [
        {
            "status": "failed",
            "filename": "private-a.pdf",
            "last_error": private_error,
            "records_imported": 4,
            "pages_needing_ocr": [],
            "attempt_count": 1,
        },
        {
            "status": "failed",
            "filename": "private-b.pdf",
            "last_error": private_error,
            "records_flagged": 2,
            "pages_needing_ocr": [3],
            "attempt_count": 2,
        },
        {"status": "failed", "last_error": "other failure", "records_imported": 9},
    ]

    result = summarize_schema_cache_partial_activity(jobs)

    assert result == {
        "failed_schema_cache_jobs": 2,
        "failed_schema_cache_jobs_with_record_activity": 2,
        "failed_schema_cache_jobs_with_activity_without_ocr": 1,
        "failed_schema_cache_jobs_with_activity_retried": 1,
        "failed_schema_cache_jobs_for_read_only_reconciliation": 1,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
    }
    rendered = str(result)
    assert "private-a.pdf" not in rendered
    assert "private-b.pdf" not in rendered
    assert private_error not in rendered


def test_schema_cache_without_partial_activity_is_not_reconciliation_candidate():
    result = summarize_schema_cache_partial_activity([
        {
            "status": "failed",
            "last_error": "PGRST204 missing field in schema cache",
            "records_imported": 0,
            "attempt_count": 1,
        }
    ])

    assert result["failed_schema_cache_jobs"] == 1
    assert result["failed_schema_cache_jobs_with_record_activity"] == 0
    assert result["failed_schema_cache_jobs_for_read_only_reconciliation"] == 0
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
