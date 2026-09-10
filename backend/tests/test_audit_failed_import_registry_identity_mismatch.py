from scripts.audit_failed_import_registry_identity_mismatch import (
    duplicate_error_target,
    normalized_artifact_identity,
    summarize_failed_import_registry_identity_mismatch,
)


def test_normalized_identity_strips_known_local_suffixes_only():
    assert normalized_artifact_identity(
        "847921086-Manuale-Dei-Mostri-5e_ok_1787286581630.pdf"
    ) == normalized_artifact_identity("847921086-Manuale-Dei-Mostri-5e.pdf")
    assert normalized_artifact_identity("Book_1787286581630.pdf") == "book"
    assert normalized_artifact_identity("Book-v2.pdf") == "bookv2"


def test_duplicate_error_target_extracts_only_declared_duplicate_filename():
    assert duplicate_error_target("manual_source_duplicate:Book.pdf") == "Book.pdf"
    assert duplicate_error_target("MANUAL_SOURCE_DUPLICATE: Book_ok.pdf") == "Book_ok.pdf"
    assert duplicate_error_target("manual_source_missing") is None
    assert duplicate_error_target("manual_source_duplicate:") is None


def test_audit_flags_unique_registry_identity_with_mismatched_sha_and_pages():
    jobs = [
        {
            "id": "monster-job",
            "filename": "847921086-Manuale-Dei-Mostri-5e_ok_1787286581630.pdf",
            "source_fingerprint": "a" * 64,
            "status": "failed",
            "page_count": 321,
        }
    ]
    sources = [
        {
            "id": "monster-source",
            "physical_filename": "847921086-Manuale-Dei-Mostri-5e.pdf",
            "physical_sha256": "b" * 64,
            "physical_pages": 352,
        }
    ]

    result = summarize_failed_import_registry_identity_mismatch(jobs, sources)

    assert result["failed_jobs_examined"] == 1
    assert result["failed_jobs_with_normalized_registry_identity_candidate"] == 1
    assert result["failed_jobs_with_fingerprint_mismatch"] == 1
    assert result["failed_jobs_with_page_count_mismatch"] == 1
    assert result["mismatched_failed_job_ids"] == ["monster-job"]
    assert result["registry_identity_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_audit_does_not_claim_mismatch_for_equal_fingerprint_and_pages():
    jobs = [
        {
            "id": "safe-looking-job",
            "filename": "Book_ok_1787286581630.pdf",
            "source_fingerprint": "c" * 64,
            "status": "failed",
            "page_count": 100,
        }
    ]
    sources = [
        {
            "id": "source",
            "physical_filename": "Book.pdf",
            "physical_sha256": "c" * 64,
            "physical_pages": 100,
        }
    ]

    result = summarize_failed_import_registry_identity_mismatch(jobs, sources)

    assert result["failed_jobs_with_normalized_registry_identity_candidate"] == 1
    assert result["failed_jobs_with_fingerprint_mismatch"] == 0
    assert result["failed_jobs_with_page_count_mismatch"] == 0
    assert result["mismatched_failed_job_ids"] == []
    assert result["automatic_retry_authorized"] is False


def test_audit_treats_multiple_registry_candidates_as_ambiguous():
    jobs = [
        {
            "id": "ambiguous-job",
            "filename": "Book_1787286581630.pdf",
            "source_fingerprint": "a" * 64,
            "status": "failed",
            "page_count": 100,
        }
    ]
    sources = [
        {"id": "s1", "physical_filename": "Book.pdf", "physical_sha256": "a" * 64},
        {"id": "s2", "physical_filename": "Book_ok.pdf", "physical_sha256": "b" * 64},
    ]

    result = summarize_failed_import_registry_identity_mismatch(jobs, sources)

    assert result["failed_jobs_with_normalized_registry_identity_candidate"] == 1
    assert result["failed_jobs_with_ambiguous_registry_identity_candidate"] == 1
    assert result["failed_jobs_with_fingerprint_mismatch"] == 0
    assert result["mismatched_failed_job_ids"] == []


def test_audit_flags_duplicate_claim_that_crosses_normalized_artifact_identity():
    jobs = [
        {
            "id": "monster-job",
            "filename": "847921086-Manuale-Dei-Mostri-5e_ok_1787286581630.pdf",
            "status": "failed",
            "last_error": "manual_source_duplicate:Manuale_del_giocatore__1787259882002.pdf",
        }
    ]

    result = summarize_failed_import_registry_identity_mismatch(jobs, [])

    assert result["failed_jobs_with_duplicate_claim"] == 1
    assert result["failed_jobs_with_cross_identity_duplicate_claim"] == 1
    assert result["cross_identity_duplicate_failed_job_ids"] == ["monster-job"]
    assert result["cross_identity_duplicate_requires_manual_reconciliation"] is True
    assert result["duplicate_target_identity_is_diagnostic_only"] is True
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_audit_accepts_duplicate_claim_with_same_normalized_identity_as_diagnostic_only():
    jobs = [
        {
            "id": "same-book-job",
            "filename": "Book_ok_1787286581630.pdf",
            "status": "failed",
            "last_error": "manual_source_duplicate:Book.pdf",
        }
    ]

    result = summarize_failed_import_registry_identity_mismatch(jobs, [])

    assert result["failed_jobs_with_duplicate_claim"] == 1
    assert result["failed_jobs_with_cross_identity_duplicate_claim"] == 0
    assert result["cross_identity_duplicate_failed_job_ids"] == []
    assert result["cross_identity_duplicate_requires_manual_reconciliation"] is False
    assert result["automatic_retry_authorized"] is False


def test_audit_confirms_distinct_registry_logical_sources_for_cross_identity_duplicate_claim():
    jobs = [
        {
            "id": "monster-job",
            "filename": "847921086-Manuale-Dei-Mostri-5e_ok_1787286581630.pdf",
            "status": "failed",
            "last_error": "manual_source_duplicate:Manuale_del_giocatore__1787259882002.pdf",
        }
    ]
    sources = [
        {
            "id": "monster-source",
            "physical_filename": "847921086-Manuale-Dei-Mostri-5e.pdf",
            "logical_source_id": "mm_2014_it",
        },
        {
            "id": "phb-source",
            "physical_filename": "Manuale del giocatore .pdf",
            "logical_source_id": "phb_2014_it",
        },
    ]

    result = summarize_failed_import_registry_identity_mismatch(jobs, sources)

    assert result["failed_jobs_with_cross_identity_duplicate_claim"] == 1
    assert result["failed_jobs_with_registry_distinct_logical_source_duplicate_claim"] == 1
    assert result["registry_distinct_logical_source_duplicate_failed_job_ids"] == ["monster-job"]
    assert result["registry_logical_source_evidence_is_diagnostic_only"] is True
    assert result["registry_distinct_logical_source_duplicate_requires_manual_reconciliation"] is True
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False


def test_audit_does_not_escalate_when_registry_logical_source_is_the_same():
    jobs = [
        {
            "id": "variant-job",
            "filename": "Book-A_ok_1787286581630.pdf",
            "status": "failed",
            "last_error": "manual_source_duplicate:Book-B.pdf",
        }
    ]
    sources = [
        {
            "id": "source-a",
            "physical_filename": "Book-A.pdf",
            "logical_source_id": "same_book",
        },
        {
            "id": "source-b",
            "physical_filename": "Book-B.pdf",
            "logical_source_id": "same_book",
        },
    ]

    result = summarize_failed_import_registry_identity_mismatch(jobs, sources)

    assert result["failed_jobs_with_cross_identity_duplicate_claim"] == 1
    assert result["failed_jobs_with_registry_distinct_logical_source_duplicate_claim"] == 0
    assert result["registry_distinct_logical_source_duplicate_failed_job_ids"] == []
    assert result["registry_distinct_logical_source_duplicate_requires_manual_reconciliation"] is False
    assert result["automatic_retry_authorized"] is False
