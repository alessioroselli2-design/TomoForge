from scripts.audit_failed_import_source_provenance import (
    summarize_failed_import_source_provenance,
)


def test_requires_exact_hash_when_fingerprint_exists():
    sources = [
        {"physical_filename": "Book.pdf", "physical_sha256": "aaa"},
        {"physical_filename": "Other.pdf", "physical_sha256": "bbb"},
    ]
    jobs = [
        {
            "filename": "Book.pdf",
            "source_fingerprint": "ccc",
            "status": "failed",
            "last_error": "manual_source_missing",
        },
        {
            "filename": "Renamed.pdf",
            "source_fingerprint": "bbb",
            "status": "failed",
            "last_error": "manual_source_missing",
        },
    ]

    result = summarize_failed_import_source_provenance(sources, jobs)

    assert result["failed_source_jobs_total"] == 2
    assert result["exact_sha_matches"] == 1
    assert result["filename_matches_without_hash_confirmation"] == 1
    assert result["unresolved_no_exact_registry_evidence"] == 0
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False


def test_unresolved_and_duplicate_target_do_not_become_safe_match():
    sources = [
        {"physical_filename": "Existing.pdf", "physical_sha256": "aaa"},
    ]
    jobs = [
        {
            "filename": "Missing.pdf",
            "source_fingerprint": "ccc",
            "status": "failed",
            "last_error": "manual_source_missing",
        },
        {
            "filename": "Duplicate.pdf",
            "source_fingerprint": "ddd",
            "status": "failed",
            "last_error": "manual_source_duplicate:Existing.pdf",
        },
    ]

    result = summarize_failed_import_source_provenance(sources, jobs)

    assert result["failed_source_jobs_total"] == 2
    assert result["unresolved_no_exact_registry_evidence"] == 2
    assert result["reported_duplicate_targets_present_in_registry"] == 1
    assert result["exact_sha_matches"] == 0
    assert result["ocr_generation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_ambiguous_hash_never_authorizes_retry():
    sources = [
        {"physical_filename": "A.pdf", "physical_sha256": "same"},
        {"physical_filename": "B.pdf", "physical_sha256": "same"},
    ]
    jobs = [
        {
            "filename": "Unknown.pdf",
            "source_fingerprint": "same",
            "status": "failed",
            "last_error": "manual_source_duplicate:A.pdf",
        }
    ]

    result = summarize_failed_import_source_provenance(sources, jobs)

    assert result["ambiguous_sha_matches"] == 1
    assert result["exact_sha_matches"] == 0
    assert result["automatic_retry_authorized"] is False
