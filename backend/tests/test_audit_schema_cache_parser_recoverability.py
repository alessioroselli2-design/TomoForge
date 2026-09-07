from scripts.audit_schema_cache_parser_recoverability import summarize_schema_cache_parser_recoverability


def _job(filename="Book_123.pdf", page_count=4, pages_needing_ocr=None):
    return {
        "status": "failed",
        "filename": filename,
        "page_count": page_count,
        "current_page": 2,
        "records_imported": 1,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "pages_needing_ocr": pages_needing_ocr or [],
        "last_error": "{'code': 'PGRST204', 'message': \"Could not find the 'level' column in the schema cache\"}",
    }


def _source(text_mode="text", filename="Book_123.pdf", status="active"):
    return {"physical_filename": filename, "source_status": status, "text_mode": text_mode}


def _record(*pages, filename="Book_123.pdf"):
    return {"source_refs": [{"filename": filename, "page": p} for p in pages]}


def test_text_source_classifies_missing_pages_as_parser_candidates():
    result = summarize_schema_cache_parser_recoverability(
        [_job(pages_needing_ocr=[4])], [_source("text")], [_record(1, 2)]
    )
    assert result["unresolved_pages_total"] == 2
    assert result["parser_only_candidate_pages"] == 1
    assert result["ocr_required_pages_from_existing_evidence"] == 1
    assert result["indeterminate_pages_requiring_page_level_evidence"] == 0
    assert result["parser_recovery_executed"] is False
    assert result["ocr_executed"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_mixed_source_stays_indeterminate_without_page_evidence():
    result = summarize_schema_cache_parser_recoverability(
        [_job()], [_source("mixed")], [_record(1, 2)]
    )
    assert result["parser_only_candidate_pages"] == 0
    assert result["ocr_required_pages_from_existing_evidence"] == 0
    assert result["indeterminate_pages_requiring_page_level_evidence"] == 2


def test_vision_source_classifies_missing_pages_as_ocr_required_but_does_not_authorize_it():
    result = summarize_schema_cache_parser_recoverability(
        [_job()], [_source("vision_required")], [_record(1)]
    )
    assert result["unresolved_pages_total"] == 3
    assert result["ocr_required_pages_from_existing_evidence"] == 3
    assert result["ocr_executed"] is False
    assert result["automatic_retry_authorized"] is False


def test_missing_or_ambiguous_source_is_not_guessed():
    result = summarize_schema_cache_parser_recoverability(
        [_job()], [_source("text", status="duplicate")], [_record(1)]
    )
    assert result["jobs_with_unambiguous_active_source"] == 0
    assert result["jobs_with_ambiguous_or_missing_source"] == 1
    assert result["unresolved_pages_total"] == 0
