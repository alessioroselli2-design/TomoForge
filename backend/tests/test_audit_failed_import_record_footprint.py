from scripts.audit_failed_import_record_footprint import (
    summarize_failed_import_record_footprint,
)


def test_failed_import_record_footprint_counts_exact_source_keys_only():
    jobs = [
        {"id": "player-job", "status": "failed", "filename": "player.pdf"},
        {"id": "tasha-job", "status": "failed", "filename": "tasha.pdf"},
        {"id": "xanathar-job", "status": "completed", "filename": "xanathar.pdf"},
    ]
    records = [
        {"source_key": "player.pdf", "review_status": "verified"},
        {"source_key": "player.pdf", "review_status": "needs_review"},
        {"source_key": "tasha.pdf", "review_status": "pending"},
        {"source_key": "xanathar.pdf", "review_status": "verified"},
        {"source_key": "PLAYER.PDF", "review_status": "verified"},
    ]

    result = summarize_failed_import_record_footprint(jobs, records)

    assert result["failed_jobs_total"] == 2
    assert result["failed_jobs_with_exact_record_footprint"] == 2
    assert result["failed_jobs_without_exact_record_footprint"] == 0
    assert result["unresolved_failed_job_ids"] == []
    assert result["records_exactly_linked_to_failed_jobs"] == 3
    assert result["linked_records_verified"] == 1
    assert result["linked_records_needs_review"] == 1
    assert result["linked_records_pending"] == 1
    assert result["linked_records_other_review_states"] == 0


def test_failed_import_without_exact_records_stays_unresolved_and_gates_closed():
    result = summarize_failed_import_record_footprint(
        [{"id": "manual-job", "status": "failed", "filename": "manual.pdf"}],
        [{"source_key": "other.pdf", "review_status": "verified"}],
    )

    assert result["failed_jobs_with_exact_record_footprint"] == 0
    assert result["failed_jobs_without_exact_record_footprint"] == 1
    assert result["unresolved_failed_job_ids"] == ["manual-job"]
    assert result["records_exactly_linked_to_failed_jobs"] == 0
    assert result["record_set_completeness_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_only_unresolved_failed_job_ids_are_exposed_without_filenames():
    result = summarize_failed_import_record_footprint(
        [
            {"id": "linked-job", "status": "failed", "filename": "linked-private.pdf"},
            {"id": "missing-job", "status": "failed", "filename": "missing-private.pdf"},
        ],
        [{"source_key": "linked-private.pdf", "review_status": "verified"}],
    )

    assert result["unresolved_failed_job_ids"] == ["missing-job"]
    assert "linked-private.pdf" not in str(result)
    assert "missing-private.pdf" not in str(result)


def test_private_filenames_are_not_rendered_in_summary():
    filename = "private-secret.pdf"
    result = summarize_failed_import_record_footprint(
        [{"id": "private-job", "status": "failed", "filename": filename}],
        [{"source_key": filename, "review_status": "conflict"}],
    )

    assert filename not in str(result)
    assert result["unresolved_failed_job_ids"] == []
    assert result["linked_records_other_review_states"] == 1
    assert result["exact_source_key_evidence_only"] is True
