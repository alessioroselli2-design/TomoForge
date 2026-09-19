from scripts.audit_schema_cache_page_provenance import (
    summarize_schema_cache_page_provenance,
)


def _job(**overrides):
    job = {
        "status": "failed",
        "last_error": "PGRST204 schema cache",
        "records_imported": 2,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "current_page": 10,
        "page_count": 20,
        "filename": "Manuale_1700000000000.pdf",
    }
    job.update(overrides)
    return job


def test_numeric_page_refs_are_measured_but_not_treated_as_completeness_proof():
    jobs = [_job()]
    records = [
        {
            "id": "r1",
            "source_refs": [{"filename": "Manuale.pdf", "page": 4}],
        },
        {
            "id": "r2",
            "source_refs": [{"filename": "Manuale_1700000000999.pdf", "page": 10.0}],
        },
    ]

    result = summarize_schema_cache_page_provenance(jobs, records)

    assert result["schema_cache_failures_with_progress_gap"] == 1
    assert result["nominal_missing_pages"] == 10
    assert result["jobs_with_page_provenance"] == 1
    assert result["records_with_matching_source_refs"] == 2
    assert result["distinct_pages_observed"] == 2
    assert result["jobs_refs_reach_reported_progress"] == 1
    assert result["jobs_refs_reach_declared_end"] == 0
    assert result["record_set_completeness_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_declared_end_observation_still_does_not_confirm_completeness():
    jobs = [_job()]
    records = [
        {
            "id": "r1",
            "source_refs": [{"filename": "Manuale.pdf", "page": "20"}],
        }
    ]

    result = summarize_schema_cache_page_provenance(jobs, records)

    assert result["jobs_refs_reach_declared_end"] == 1
    assert result["record_set_completeness_confirmed"] is False
    assert result["automatic_retry_authorized"] is False


def test_invalid_page_values_are_ignored_without_losing_matching_record_signal():
    jobs = [_job()]
    records = [
        {
            "id": "r1",
            "source_refs": [
                {"filename": "Manuale.pdf", "page": True},
                {"filename": "Manuale.pdf", "page": "chapter-2"},
            ],
        }
    ]

    result = summarize_schema_cache_page_provenance(jobs, records)

    assert result["jobs_with_page_provenance"] == 0
    assert result["records_with_matching_source_refs"] == 1
    assert result["distinct_pages_observed"] == 0


def test_completed_or_page_complete_jobs_are_out_of_scope():
    jobs = [_job(status="completed"), _job(current_page=20)]

    result = summarize_schema_cache_page_provenance(jobs, [])

    assert result["schema_cache_failures_with_progress_gap"] == 0
    assert result["nominal_missing_pages"] == 0
