from scripts.audit_failed_import_registry_sha import summarize_failed_import_registry_sha


def test_registry_sha_audit_classifies_matches_conservatively():
    sources = [
        {"id": "s1", "physical_filename": "Book.pdf", "physical_sha256": "a" * 64},
        {"id": "s2", "physical_filename": "Other.pdf", "physical_sha256": "b" * 64},
        {"id": "s3", "physical_filename": "NameOnly.pdf", "physical_sha256": "c" * 64},
    ]
    jobs = [
        {
            "id": "exact",
            "filename": "BOOK.PDF",
            "source_fingerprint": "a" * 64,
            "status": "failed",
            "last_error": "manual_source_missing",
        },
        {
            "id": "sha",
            "filename": "Unknown.pdf",
            "source_fingerprint": "b" * 64,
            "status": "failed",
            "last_error": "manual_source_missing",
        },
        {
            "id": "name",
            "filename": "nameonly.pdf",
            "source_fingerprint": "d" * 64,
            "status": "failed",
            "last_error": "manual_source_duplicate:Elsewhere.pdf",
        },
        {
            "id": "none",
            "filename": "Absent.pdf",
            "source_fingerprint": "e" * 64,
            "status": "failed",
            "last_error": "manual_source_missing",
        },
        {
            "id": "ignored",
            "filename": "Book.pdf",
            "source_fingerprint": "a" * 64,
            "status": "failed",
            "last_error": "schema cache failure",
        },
    ]

    result = summarize_failed_import_registry_sha(jobs, sources)

    assert result["failed_source_jobs_total"] == 4
    assert result["exact_filename_and_sha"] == 1
    assert result["sha_only"] == 1
    assert result["filename_only"] == 1
    assert result["no_registry_match"] == 1
    assert result["ambiguous_registry_match"] == 0
    assert [job["classification"] for job in result["jobs"]] == [
        "exact_filename_and_sha",
        "sha_only",
        "filename_only",
        "no_registry_match",
    ]
    assert result["evidence_is_diagnostic_only"] is True
    assert result["registry_write_authorized"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["ocr_generation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_registry_sha_audit_marks_conflicting_filename_and_sha_ambiguous():
    sources = [
        {"id": "by-name", "physical_filename": "Book.pdf", "physical_sha256": "a" * 64},
        {"id": "by-sha", "physical_filename": "Else.pdf", "physical_sha256": "b" * 64},
    ]
    jobs = [
        {
            "id": "conflict",
            "filename": "Book.pdf",
            "source_fingerprint": "b" * 64,
            "status": "failed",
            "last_error": "manual_source_missing",
        }
    ]

    result = summarize_failed_import_registry_sha(jobs, sources)

    assert result["ambiguous_registry_match"] == 1
    assert result["jobs"][0]["classification"] == "ambiguous_registry_match"
    assert result["jobs"][0]["registry_source_ids"] == ["by-name", "by-sha"]
