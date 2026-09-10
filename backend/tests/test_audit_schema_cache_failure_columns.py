from scripts.audit_schema_cache_failure_columns import summarize_schema_cache_failure_columns


def test_named_schema_cache_columns_are_aggregated_without_authorizing_recovery():
    jobs = [
        {"status": "completed"},
        {
            "status": "failed",
            "last_error": "{'message': \"Could not find the 'level' column of 'private_reference_records' in the schema cache\", 'code': 'PGRST204'}",
        },
        {
            "status": "failed",
            "last_error": "PGRST204: Could not find column in the schema cache",
        },
        {"status": "failed", "last_error": "manual_source_missing"},
    ]

    result = summarize_schema_cache_failure_columns(jobs)

    assert result["failed_jobs_total"] == 3
    assert result["schema_cache_failures_total"] == 2
    assert result["schema_cache_missing_column_breakdown"] == {"level": 1, "unknown": 1}
    assert result["requires_live_schema_recheck_before_recovery"] is True
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["ocr_generation_authorized"] is False
    assert result["translation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_no_schema_cache_failures_produces_empty_breakdown():
    result = summarize_schema_cache_failure_columns(
        [{"status": "completed"}, {"status": "failed", "last_error": "manual_source_missing"}]
    )

    assert result["schema_cache_failures_total"] == 0
    assert result["schema_cache_missing_column_breakdown"] == {}
    assert result["requires_live_schema_recheck_before_recovery"] is False
    assert result["automatic_retry_authorized"] is False
