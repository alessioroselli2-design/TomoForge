from scripts.audit_catalogued_vision_zero_import import summarize_catalogued_vision_zero_import


def test_catalogued_vision_zero_import_gate_is_conservative():
    sources = [
        {
            "id": "blocked-vision",
            "source_status": "active",
            "import_state": "catalogued",
            "text_mode": "vision_required",
            "imported_record_count": 0,
            "physical_sha256": "a" * 64,
            "physical_filename": "Vision.pdf",
        },
        {
            "id": "blocked-mixed",
            "source_status": "active",
            "import_state": "catalogued",
            "text_mode": "mixed",
            "imported_record_count": None,
            "physical_sha256": "b" * 64,
            "physical_filename": "Mixed.pdf",
        },
        {
            "id": "already-imported",
            "source_status": "active",
            "import_state": "catalogued",
            "text_mode": "vision_required",
            "imported_record_count": 4,
        },
        {
            "id": "plain-text",
            "source_status": "active",
            "import_state": "catalogued",
            "text_mode": "text",
            "imported_record_count": 0,
        },
        {
            "id": "inactive",
            "source_status": "superseded",
            "import_state": "catalogued",
            "text_mode": "vision_required",
            "imported_record_count": 0,
        },
    ]
    jobs = [
        {
            "id": "exact",
            "filename": "Other.pdf",
            "source_fingerprint": "a" * 64,
        },
        {
            "id": "filename-only",
            "filename": "Mixed.pdf",
            "source_fingerprint": "c" * 64,
        },
    ]

    result = summarize_catalogued_vision_zero_import(sources, jobs)

    assert result["active_catalogued_vision_sources_examined"] == 3
    assert result["active_catalogued_vision_sources_with_zero_imported_records"] == 2
    assert result["blocked_source_ids"] == ["blocked-mixed", "blocked-vision"]
    assert result["zero_import_sources_with_exact_import_job_evidence"] == 1
    assert result["zero_import_sources_with_filename_only_job_evidence"] == 1
    assert result["zero_import_sources_with_ambiguous_job_evidence"] == 0
    assert result["zero_import_sources_without_exact_import_job_evidence"] == 0
    assert result["source_ids_with_exact_import_job_evidence"] == ["blocked-vision"]
    assert result["source_ids_with_filename_only_job_evidence"] == ["blocked-mixed"]
    assert result["requires_authorized_text_extraction_before_import"] is True
    assert result["historical_import_job_evidence_is_diagnostic_only"] is True
    assert result["evidence_is_diagnostic_only"] is True
    assert result["ocr_authorized"] is False
    assert result["external_processing_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_catalogued_vision_zero_import_reports_missing_and_ambiguous_job_evidence():
    sources = [
        {
            "id": "missing",
            "source_status": "active",
            "import_state": "catalogued",
            "text_mode": "vision_required",
            "imported_record_count": 0,
            "physical_sha256": "d" * 64,
            "physical_filename": "Missing.pdf",
        },
        {
            "id": "ambiguous",
            "source_status": "active",
            "import_state": "catalogued",
            "text_mode": "mixed",
            "imported_record_count": 0,
            "physical_sha256": "e" * 64,
            "physical_filename": "Ambiguous.pdf",
        },
    ]
    jobs = [
        {"id": "by-sha", "filename": "Else.pdf", "source_fingerprint": "e" * 64},
        {
            "id": "by-filename",
            "filename": "Ambiguous.pdf",
            "source_fingerprint": "f" * 64,
        },
    ]

    result = summarize_catalogued_vision_zero_import(sources, jobs)

    assert result["zero_import_sources_with_ambiguous_job_evidence"] == 1
    assert result["source_ids_with_ambiguous_job_evidence"] == ["ambiguous"]
    assert result["zero_import_sources_without_exact_import_job_evidence"] == 1
    assert result["source_ids_without_exact_import_job_evidence"] == ["missing"]
    assert result["automatic_retry_authorized"] is False


def test_catalogued_vision_zero_import_gate_can_be_clear():
    result = summarize_catalogued_vision_zero_import(
        [
            {
                "id": "done",
                "source_status": "active",
                "import_state": "catalogued",
                "text_mode": "vision_required",
                "imported_record_count": 1,
            }
        ]
    )

    assert result["active_catalogued_vision_sources_examined"] == 1
    assert result["active_catalogued_vision_sources_with_zero_imported_records"] == 0
    assert result["blocked_source_ids"] == []
    assert result["zero_import_sources_with_exact_import_job_evidence"] == 0
    assert result["zero_import_sources_without_exact_import_job_evidence"] == 0
    assert result["requires_authorized_text_extraction_before_import"] is False
