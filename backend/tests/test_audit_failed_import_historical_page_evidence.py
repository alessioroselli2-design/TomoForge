from pathlib import Path

from scripts.audit_failed_import_historical_page_evidence import (
    _load_historical_page_counts,
    summarize_failed_import_historical_page_evidence,
)


def test_loads_exact_filename_page_counts_from_multiple_reports(tmp_path: Path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text('[{"filename":"Book.PDF","pages":10}]', encoding="utf-8")
    second.write_text(
        '[{"filename":"book.pdf","pages":10},{"filename":"Other.pdf","pages":20}]',
        encoding="utf-8",
    )

    assert _load_historical_page_counts((first, second)) == {
        "book.pdf": {10},
        "other.pdf": {20},
    }


def test_page_count_corroboration_is_diagnostic_only():
    jobs = [
        {
            "id": "one",
            "filename": "Bardo.pdf",
            "source_fingerprint": "a" * 64,
            "status": "failed",
            "page_count": 26,
            "last_error": "manual_source_missing",
        },
        {
            "id": "two",
            "filename": "Mismatch.pdf",
            "source_fingerprint": "b" * 64,
            "status": "failed",
            "page_count": 99,
            "last_error": "manual_source_missing",
        },
        {
            "id": "three",
            "filename": "Absent.pdf",
            "source_fingerprint": "c" * 64,
            "status": "failed",
            "page_count": 5,
            "last_error": "manual_source_duplicate:Elsewhere.pdf",
        },
        {
            "id": "ignored",
            "filename": "Bardo.pdf",
            "status": "failed",
            "page_count": 26,
            "last_error": "schema cache failure",
        },
    ]

    result = summarize_failed_import_historical_page_evidence(
        jobs,
        {"bardo.pdf": {26}, "mismatch.pdf": {100}},
    )

    assert result["failed_source_jobs_total"] == 3
    assert result["exact_historical_filename_and_page_count_matches"] == 1
    assert result["historical_filename_page_mismatches"] == 1
    assert result["failed_jobs_without_historical_filename"] == 1
    assert result["matched_jobs"] == [
        {
            "job_id": "one",
            "filename": "Bardo.pdf",
            "page_count": 26,
            "source_fingerprint": "a" * 64,
        }
    ]
    assert result["evidence_is_diagnostic_only"] is True
    assert result["registry_write_authorized"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["ocr_generation_authorized"] is False
    assert result["canonicalization_authorized"] is False
