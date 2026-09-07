from pathlib import Path

from scripts.audit_failed_import_source_provenance import (
    _declared_ocr_gap_pages,
    _historical_filenames_from_sample_report,
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
            "pages_needing_ocr": [1, 1, "2", 0, "bad"],
        },
        {
            "filename": "Duplicate.pdf",
            "source_fingerprint": "ddd",
            "status": "failed",
            "last_error": "manual_source_duplicate:Existing.pdf",
            "pages_needing_ocr": [],
        },
    ]

    result = summarize_failed_import_source_provenance(
        sources,
        jobs,
        historical_filenames={"missing.pdf", "existing.pdf"},
    )

    assert result["failed_source_jobs_total"] == 2
    assert result["failed_source_jobs_with_declared_ocr_gaps"] == 1
    assert result["declared_ocr_gap_pages_total"] == 2
    assert result["unresolved_no_exact_registry_evidence"] == 2
    assert result["reported_duplicate_targets_present_in_registry"] == 1
    assert result["failed_job_filenames_present_in_historical_artifacts"] == 1
    assert result["reported_duplicate_targets_present_in_historical_artifacts"] == 1
    assert result["historical_artifact_evidence_is_diagnostic_only"] is True
    assert result["ocr_gap_evidence_is_diagnostic_only"] is True
    assert result["exact_sha_matches"] == 0
    assert result["automatic_retry_authorized"] is False
    assert result["ocr_generation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_declared_ocr_gap_pages_are_normalized_without_authorizing_ocr():
    assert _declared_ocr_gap_pages({"pages_needing_ocr": [3, "2", 3, -1, None]}) == [2, 3]
    assert _declared_ocr_gap_pages({"pages_needing_ocr": "1,2"}) == []

    result = summarize_failed_import_source_provenance(
        [],
        [
            {
                "filename": "Missing.pdf",
                "source_fingerprint": "sha",
                "status": "failed",
                "last_error": "manual_source_missing",
                "pages_needing_ocr": [4],
            },
            {
                "filename": "Schema.pdf",
                "source_fingerprint": "sha2",
                "status": "failed",
                "last_error": "schema cache failure",
                "pages_needing_ocr": [9],
            },
        ],
    )

    assert result["failed_source_jobs_with_declared_ocr_gaps"] == 1
    assert result["declared_ocr_gap_pages_total"] == 1
    assert result["ocr_generation_authorized"] is False


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


def test_sample_report_loader_uses_exact_casefolded_filenames(tmp_path: Path):
    report = tmp_path / "report.json"
    report.write_text(
        '[{"filename":"Manual.PDF"},{"filename":""},{"other":"ignored"}]',
        encoding="utf-8",
    )

    assert _historical_filenames_from_sample_report(report) == {"manual.pdf"}
    assert _historical_filenames_from_sample_report(tmp_path / "missing.json") == set()
