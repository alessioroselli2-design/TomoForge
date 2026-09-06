from scripts.audit_schema_cache_record_completeness import (
    summarize_schema_cache_record_completeness,
)


def test_completion_candidate_requires_end_progress_exact_records_and_no_ocr():
    filename = "manual_1787259882002.pdf"
    result = summarize_schema_cache_record_completeness(
        [
            {
                "status": "failed",
                "filename": filename,
                "last_error": "PGRST204 schema cache private payload",
                "records_imported": 12,
                "current_page": 320,
                "page_count": 320,
                "pages_needing_ocr": [],
            }
        ],
        [{"source_key": filename}],
    )

    assert result == {
        "schema_cache_failures_with_record_activity": 1,
        "with_exact_record_source_key_provenance": 1,
        "with_page_progress_reaching_declared_end": 1,
        "without_ocr_backlog": 1,
        "completion_review_candidates": 1,
        "record_set_completeness_confirmed": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "canonicalization_authorized": False,
    }


def test_partial_page_progress_never_becomes_completion_candidate():
    filename = "manual_1787259882002.pdf"
    result = summarize_schema_cache_record_completeness(
        [
            {
                "status": "failed",
                "filename": filename,
                "last_error": "PGRST204 schema cache",
                "records_updated": 4,
                "current_page": 87,
                "page_count": 320,
                "pages_needing_ocr": [],
            }
        ],
        [{"source_key": filename}],
    )

    assert result["with_page_progress_reaching_declared_end"] == 0
    assert result["completion_review_candidates"] == 0
    assert result["record_set_completeness_confirmed"] is False


def test_ocr_backlog_blocks_candidate_even_at_declared_end():
    filename = "manual.pdf"
    result = summarize_schema_cache_record_completeness(
        [
            {
                "status": "failed",
                "filename": filename,
                "last_error": "PGRST204 schema cache",
                "records_flagged": 2,
                "current_page": 100,
                "page_count": 100,
                "pages_needing_ocr": [9],
            }
        ],
        [{"source_key": filename}],
    )

    assert result["without_ocr_backlog"] == 0
    assert result["completion_review_candidates"] == 0
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_private_identifiers_and_errors_are_not_rendered():
    filename = "private-secret-manual.pdf"
    private_error = "PGRST204 schema cache secret detail"
    result = summarize_schema_cache_record_completeness(
        [
            {
                "status": "failed",
                "filename": filename,
                "last_error": private_error,
                "records_skipped": 1,
                "current_page": 1,
                "page_count": 2,
                "pages_needing_ocr": [],
            }
        ],
        [{"source_key": filename}],
    )

    rendered = str(result)
    assert filename not in rendered
    assert private_error not in rendered
