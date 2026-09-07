from scripts.audit_failed_import_failure_classes import summarize_failed_import_failure_classes


def test_failure_classes_are_separated_without_authorizing_retry():
    jobs = [
        {"status": "completed"},
        {
            "status": "failed",
            "last_error": "PGRST204: Could not find column in the schema cache",
            "records_imported": 2,
            "attempt_count": 3,
            "pages_needing_ocr": [],
        },
        {
            "status": "failed",
            "last_error": "manual_source_duplicate:hidden.pdf",
            "pages_needing_ocr": [],
        },
        {
            "status": "failed",
            "last_error": "manual_source_missing",
            "records_updated": 4,
            "pages_needing_ocr": [1],
        },
        {
            "status": "failed",
            "last_error": "manual_source_missing",
            "pages_needing_ocr": [],
        },
        {"status": "failed", "last_error": "timeout", "pages_needing_ocr": []},
    ]

    result = summarize_failed_import_failure_classes(jobs)

    assert result == {
        "failed_jobs_total": 5,
        "failure_class_breakdown": {
            "manual_source_duplicate": 1,
            "manual_source_missing": 2,
            "other": 1,
            "schema_cache": 1,
        },
        "failed_jobs_with_record_activity": 2,
        "failed_jobs_with_ocr_backlog": 1,
        "schema_cache_retry_candidates": 0,
        "manual_source_missing_jobs": 2,
        "manual_source_missing_investigation_candidates": 1,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "ocr_generation_authorized": False,
        "translation_authorized": False,
        "canonicalization_authorized": False,
    }
    assert "hidden.pdf" not in str(result)
    assert "PGRST204" not in str(result)


def test_clean_history_has_no_failed_jobs_and_still_does_not_authorize_writes():
    result = summarize_failed_import_failure_classes([{"status": "completed"}])
    assert result["failed_jobs_total"] == 0
    assert result["failure_class_breakdown"] == {}
    assert result["schema_cache_retry_candidates"] == 0
    assert result["manual_source_missing_jobs"] == 0
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
