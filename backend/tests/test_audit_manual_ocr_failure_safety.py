from scripts.audit_manual_ocr_failure_safety import summarize_ocr_failure_safety


def test_ocr_failure_safety_reports_partial_activity_and_retries_without_leaking_details():
    private_error = "private OCR provider error payload"
    jobs = [
        {
            "status": "failed",
            "filename": "private-a.pdf",
            "last_error": private_error,
            "pages_needing_ocr": [2, 3],
            "records_imported": 5,
            "attempt_count": 2,
        },
        {
            "status": "failed",
            "filename": "private-b.pdf",
            "pages_needing_ocr": [9],
            "records_flagged": 1,
            "attempt_count": 1,
        },
        {"status": "completed", "pages_needing_ocr": [7]},
    ]

    result = summarize_ocr_failure_safety(jobs)

    assert result == {
        "failed_jobs_with_ocr_backlog": 2,
        "failed_ocr_jobs_with_record_activity": 2,
        "failed_ocr_jobs_retried": 1,
        "failed_ocr_jobs_pristine_for_read_only_investigation": 0,
        "automatic_retry_authorized": False,
        "ocr_authorized": False,
    }
    rendered = str(result)
    assert "private-a.pdf" not in rendered
    assert "private-b.pdf" not in rendered
    assert private_error not in rendered


def test_pristine_ocr_failure_only_allows_read_only_investigation():
    result = summarize_ocr_failure_safety([
        {"status": "failed", "pages_needing_ocr": [4], "attempt_count": 1},
    ])

    assert result["failed_ocr_jobs_pristine_for_read_only_investigation"] == 1
    assert result["automatic_retry_authorized"] is False
    assert result["ocr_authorized"] is False


def test_non_failed_or_non_ocr_jobs_are_excluded():
    result = summarize_ocr_failure_safety([
        {"status": "completed", "pages_needing_ocr": [1]},
        {"status": "failed", "pages_needing_ocr": []},
        {"status": "failed", "pages_needing_ocr": None},
    ])

    assert result["failed_jobs_with_ocr_backlog"] == 0
    assert result["failed_ocr_jobs_with_record_activity"] == 0
    assert result["failed_ocr_jobs_retried"] == 0
    assert result["failed_ocr_jobs_pristine_for_read_only_investigation"] == 0
