from scripts.audit_schema_cache_alternate_provenance import (
    summarize_schema_cache_alternate_provenance,
)


def _job(**overrides):
    job = {
        "status": "failed",
        "last_error": "PGRST204 schema cache",
        "records_imported": 3,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "current_page": 10,
        "page_count": 20,
        "filename": "Manuale_1700000000000.pdf",
    }
    job.update(overrides)
    return job


def test_alternate_record_provenance_is_review_signal_not_coverage_proof():
    jobs = [_job()]
    sources = [
        {
            "physical_filename": "Manuale.pdf",
            "logical_source_id": "logical-1",
            "source_status": "active",
        },
        {
            "physical_filename": "Manuale-alt.pdf",
            "logical_source_id": "logical-1",
            "source_status": "duplicate",
        },
    ]
    records = [
        {"source_key": "Manuale_1700000000000.pdf"},
        {"source_key": "Manuale-alt_1700000000001.pdf"},
    ]

    result = summarize_schema_cache_alternate_provenance(jobs, sources, records)

    assert result["schema_cache_failures_with_progress_gap"] == 1
    assert result["with_reconciled_logical_identity"] == 1
    assert result["with_alternate_registered_source"] == 1
    assert result["with_alternate_record_provenance"] == 1
    assert result["alternate_provenance_requires_review"] is True
    assert result["missing_page_coverage_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_same_normalized_source_is_not_counted_as_alternate_provenance():
    jobs = [_job()]
    sources = [
        {
            "physical_filename": "Manuale.pdf",
            "logical_source_id": "logical-1",
            "source_status": "active",
        },
    ]
    records = [
        {"source_key": "Manuale_1700000000000.pdf"},
        {"source_key": "Manuale_1700000000999.pdf"},
    ]

    result = summarize_schema_cache_alternate_provenance(jobs, sources, records)

    assert result["with_reconciled_logical_identity"] == 1
    assert result["with_alternate_registered_source"] == 0
    assert result["with_alternate_record_provenance"] == 0
    assert result["missing_page_coverage_confirmed"] is False


def test_ambiguous_registry_identity_stays_blocked():
    jobs = [_job()]
    sources = [
        {
            "physical_filename": "Manuale.pdf",
            "logical_source_id": "logical-1",
            "source_status": "active",
        },
        {
            "physical_filename": "Manuale_1600000000000.pdf",
            "logical_source_id": "logical-2",
            "source_status": "duplicate",
        },
    ]

    result = summarize_schema_cache_alternate_provenance(jobs, sources, [])

    assert result["with_reconciled_logical_identity"] == 0
    assert result["with_ambiguous_logical_identity"] == 1
    assert result["with_alternate_record_provenance"] == 0
    assert result["missing_page_coverage_confirmed"] is False


def test_completed_or_page_complete_jobs_are_out_of_scope():
    jobs = [
        _job(status="completed"),
        _job(current_page=20),
    ]

    result = summarize_schema_cache_alternate_provenance(jobs, [], [])

    assert result["schema_cache_failures_with_progress_gap"] == 0
    assert result["alternate_provenance_requires_review"] is False
