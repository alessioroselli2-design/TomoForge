from pathlib import Path

from scripts.audit_schema_cache_existing_ocr_artifacts import summarize_existing_ocr_artifacts


def _job(filename="Book_123.pdf", page_count=4):
    return {
        "status": "failed",
        "filename": filename,
        "page_count": page_count,
        "current_page": 2,
        "records_imported": 1,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "pages_needing_ocr": [],
        "last_error": "{'code': 'PGRST204', 'message': \"Could not find the 'level' column in the schema cache\"}",
    }


def _record(*pages, filename="Book_123.pdf"):
    return {"source_refs": [{"filename": filename, "page": page} for page in pages]}


def test_preview_images_never_count_as_reusable_ocr():
    result = summarize_existing_ocr_artifacts(
        [_job()],
        [_record(1, 2)],
        [Path(".agents/outputs/manual-samples/Book_123.page-003.png")],
    )
    assert result["unresolved_pages_total"] == 2
    assert result["preview_only_gap_pages"] == 1
    assert result["explicit_reusable_ocr_gap_pages"] == 0
    assert result["preview_images_count_as_ocr_evidence"] is False
    assert result["ocr_executed"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_explicit_page_scoped_ocr_text_is_inventory_evidence_only():
    result = summarize_existing_ocr_artifacts(
        [_job()],
        [_record(1)],
        [
            Path(".agents/outputs/ocr/Book_123.page-002.ocr.txt"),
            Path(".agents/outputs/ocr/Book_123.page-003.ocr.json"),
        ],
    )
    assert result["unresolved_pages_total"] == 3
    assert result["explicit_reusable_ocr_gap_pages"] == 2
    assert result["record_set_completeness_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["ocr_executed"] is False


def test_artifact_on_already_observed_page_does_not_reduce_gap_count():
    result = summarize_existing_ocr_artifacts(
        [_job()],
        [_record(1, 2)],
        [Path(".agents/outputs/ocr/Book_123.page-002.ocr.txt")],
    )
    assert result["unresolved_pages_total"] == 2
    assert result["explicit_reusable_ocr_gap_pages"] == 0


def test_non_schema_cache_failure_is_ignored():
    job = _job()
    job["last_error"] = "manual_source_missing"
    result = summarize_existing_ocr_artifacts(
        [job],
        [],
        [Path(".agents/outputs/ocr/Book_123.page-001.ocr.txt")],
    )
    assert result["schema_cache_failures_with_record_activity"] == 0
    assert result["unresolved_pages_total"] == 0
