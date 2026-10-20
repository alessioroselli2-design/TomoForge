from scripts.audit_schema_cache_progress_deficit import (
    summarize_schema_cache_progress_deficit,
)


def test_reports_incomplete_schema_cache_progress_without_authorizing_actions():
    result = summarize_schema_cache_progress_deficit(
        [
            {
                "status": "failed",
                "filename": "manual-a.pdf",
                "last_error": "PGRST204 schema cache",
                "records_imported": 10,
                "current_page": 80,
                "page_count": 100,
                "pages_needing_ocr": [],
            },
            {
                "status": "failed",
                "filename": "manual-b.pdf",
                "last_error": "PGRST204 schema cache",
                "records_updated": 4,
                "current_page": 45,
                "page_count": 50,
                "pages_needing_ocr": [],
            },
        ]
    )

    assert result == {
        "schema_cache_failures_with_record_activity": 2,
        "with_valid_declared_page_count": 2,
        "stopped_before_declared_end": 2,
        "at_or_beyond_declared_end": 0,
        "stopped_before_end_without_ocr_backlog": 2,
        "aggregate_pages_remaining": 25,
        "progress_deficit_requires_review": True,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "ocr_authorized": False,
        "canonicalization_authorized": False,
    }


def test_completed_progress_is_not_reported_as_deficit():
    result = summarize_schema_cache_progress_deficit(
        [
            {
                "status": "failed",
                "last_error": "PGRST204 schema cache",
                "records_flagged": 2,
                "current_page": 100,
                "page_count": 100,
                "pages_needing_ocr": [],
            }
        ]
    )

    assert result["stopped_before_declared_end"] == 0
    assert result["at_or_beyond_declared_end"] == 1
    assert result["aggregate_pages_remaining"] == 0
    assert result["progress_deficit_requires_review"] is False


def test_ocr_backlog_is_not_misclassified_as_clean_progress_deficit():
    result = summarize_schema_cache_progress_deficit(
        [
            {
                "status": "failed",
                "last_error": "PGRST204 schema cache",
                "records_skipped": 1,
                "current_page": 5,
                "page_count": 10,
                "pages_needing_ocr": [6],
            }
        ]
    )

    assert result["stopped_before_declared_end"] == 1
    assert result["stopped_before_end_without_ocr_backlog"] == 0
    assert result["ocr_authorized"] is False


def test_invalid_progress_and_private_details_are_not_rendered():
    filename = "private-secret.pdf"
    private_error = "PGRST204 schema cache secret detail"
    result = summarize_schema_cache_progress_deficit(
        [
            {
                "status": "failed",
                "filename": filename,
                "last_error": private_error,
                "records_imported": 1,
                "current_page": None,
                "page_count": 0,
                "pages_needing_ocr": [],
            }
        ]
    )

    assert result["with_valid_declared_page_count"] == 0
    rendered = str(result)
    assert filename not in rendered
    assert private_error not in rendered
