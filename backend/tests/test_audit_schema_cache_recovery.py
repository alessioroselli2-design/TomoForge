from scripts.audit_schema_cache_recovery import summarize_schema_cache_recovery


def test_schema_cache_audit_detects_column_now_present_without_authorizing_retry():
    jobs = [
        {
            "status": "failed",
            "last_error": "{'message': \"Could not find the 'level' column of 'private_reference_records' in the schema cache\", 'code': 'PGRST204'}",
            "records_imported": 10,
            "records_updated": 87,
            "attempt_count": 3,
        },
        {
            "status": "failed",
            "last_error": "PGRST204: Could not find the missing_field column in the schema cache",
        },
        {"status": "failed", "last_error": "manual_source_missing"},
    ]
    records = [{"id": "r1", "level": "1", "name": "Example"}]

    result = summarize_schema_cache_recovery(jobs, records)

    assert result["failed_schema_cache_jobs"] == 2
    assert result["failed_schema_cache_columns_now_present"] == 1
    assert result["failed_schema_cache_columns_still_absent"] == 1
    assert result["now_present_with_record_activity"] == 1
    assert result["now_present_without_record_activity"] == 0
    assert result["now_present_with_prior_retry"] == 1
    assert result["now_present_with_record_activity_and_prior_retry"] == 1
    assert result["now_present_partial_jobs_requiring_manual_reconciliation"] == 1
    assert result["now_present_jobs_requiring_manual_reconciliation"] == 1
    assert result["historical_failure_may_be_stale"] is True
    assert result["prior_retry_is_review_only"] is True
    assert result["partial_retried_failure_is_review_only"] is True
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_generation_authorized"] is False
    assert result["translation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_schema_cache_audit_ignores_non_pgrst204_errors_and_does_not_leak_payloads():
    private_error = "timeout while reading private-book.pdf"
    result = summarize_schema_cache_recovery(
        [{"status": "failed", "last_error": private_error}],
        [{"id": "r1", "level": None}],
    )

    assert result["failed_schema_cache_jobs"] == 0
    assert result["historical_failure_may_be_stale"] is False
    assert result["prior_retry_is_review_only"] is False
    assert result["partial_retried_failure_is_review_only"] is False
    assert private_error not in str(result)


def test_schema_cache_audit_counts_now_present_job_without_activity_separately():
    jobs = [
        {
            "status": "failed",
            "last_error": "PGRST204: Could not find the level column in the schema cache",
            "records_imported": 0,
            "records_updated": 0,
            "attempt_count": 1,
        }
    ]
    result = summarize_schema_cache_recovery(jobs, [{"id": "r1", "level": None}])

    assert result["failed_schema_cache_columns_now_present"] == 1
    assert result["now_present_with_record_activity"] == 0
    assert result["now_present_without_record_activity"] == 1
    assert result["now_present_with_prior_retry"] == 0
    assert result["now_present_with_record_activity_and_prior_retry"] == 0
    assert result["now_present_partial_jobs_requiring_manual_reconciliation"] == 0
    assert result["now_present_jobs_requiring_manual_reconciliation"] == 0
    assert result["prior_retry_is_review_only"] is False
    assert result["partial_retried_failure_is_review_only"] is False
    assert result["automatic_retry_authorized"] is False


def test_schema_cache_audit_partial_activity_without_prior_retry_still_requires_reconciliation():
    jobs = [
        {
            "status": "failed",
            "last_error": "PGRST204: Could not find the level column in the schema cache",
            "records_updated": 4,
            "attempt_count": 1,
        }
    ]
    result = summarize_schema_cache_recovery(jobs, [{"id": "r1", "level": None}])

    assert result["now_present_with_record_activity"] == 1
    assert result["now_present_with_prior_retry"] == 0
    assert result["now_present_with_record_activity_and_prior_retry"] == 0
    assert result["now_present_partial_jobs_requiring_manual_reconciliation"] == 1
    assert result["now_present_jobs_requiring_manual_reconciliation"] == 1
    assert result["prior_retry_is_review_only"] is False
    assert result["partial_retried_failure_is_review_only"] is False
    assert result["automatic_retry_authorized"] is False


def test_schema_cache_audit_prior_retry_without_activity_still_requires_reconciliation():
    jobs = [
        {
            "status": "failed",
            "last_error": "PGRST204: Could not find the level column in the schema cache",
            "records_imported": 0,
            "records_updated": 0,
            "records_flagged": 0,
            "records_skipped": 0,
            "attempt_count": 2,
        }
    ]
    result = summarize_schema_cache_recovery(jobs, [{"id": "r1", "level": None}])

    assert result["now_present_with_record_activity"] == 0
    assert result["now_present_without_record_activity"] == 1
    assert result["now_present_with_prior_retry"] == 1
    assert result["now_present_jobs_requiring_manual_reconciliation"] == 1
    assert result["prior_retry_is_review_only"] is True
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False
