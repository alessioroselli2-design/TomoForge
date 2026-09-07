from scripts.audit_vision_required_backlog import summarize_vision_required_backlog


def test_summarizes_vision_backlog_without_authorizing_processing():
    sources = [
        {
            "physical_filename": "Manuale del giocatore .pdf",
            "text_mode": "vision_required",
            "import_state": "catalogued",
            "physical_pages": 321,
        },
        {
            "physical_filename": "Text Manual.pdf",
            "text_mode": "text",
            "import_state": "catalogued",
            "physical_pages": 100,
        },
        {
            "physical_filename": "Old Scan.pdf",
            "text_mode": "vision_required",
            "import_state": "excluded",
            "physical_pages": 50,
        },
    ]
    jobs = [
        {
            "filename": "Manuale_del_giocatore__1787259882002.pdf",
            "status": "failed",
            "page_count": 321,
            "current_page": 61,
            "last_error": "PGRST204 schema cache",
        },
        {
            "filename": "Unknown_1787000000000.pdf",
            "status": "failed",
            "page_count": 20,
            "current_page": 1,
            "last_error": "manual_source_missing",
        },
    ]

    result = summarize_vision_required_backlog(sources, jobs)

    assert result["vision_sources_total"] == 2
    assert result["vision_sources_catalogued"] == 1
    assert result["vision_sources_excluded"] == 1
    assert result["vision_pages_total"] == 371
    assert result["failed_jobs_matched_to_single_vision_source"] == 1
    assert result["failed_jobs_not_uniquely_matched_to_vision_source"] == 1
    assert result["failed_jobs_schema_cache"] == 1
    assert result["failed_jobs_source_missing"] == 1
    assert result["matched_failed_pages_remaining"] == 260
    assert result["ocr_generation_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_ambiguous_duplicate_sources_do_not_count_as_safe_match():
    sources = [
        {
            "physical_filename": "Book.pdf",
            "text_mode": "vision_required",
            "import_state": "catalogued",
            "physical_pages": 100,
        },
        {
            "physical_filename": "Book (1).pdf",
            "text_mode": "vision_required",
            "import_state": "excluded",
            "physical_pages": 100,
        },
    ]
    jobs = [
        {
            "filename": "Book_1787000000000.pdf",
            "status": "failed",
            "page_count": 100,
            "current_page": 10,
            "last_error": "manual_source_duplicate:Book.pdf",
        }
    ]

    result = summarize_vision_required_backlog(sources, jobs)

    assert result["failed_jobs_matched_to_single_vision_source"] == 0
    assert result["failed_jobs_not_uniquely_matched_to_vision_source"] == 1
    assert result["failed_jobs_source_duplicate"] == 1
    assert result["matched_failed_pages_remaining"] == 0
