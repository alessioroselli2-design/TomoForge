from scripts.audit_vision_import_coverage import summarize_vision_import_coverage


def test_vision_import_coverage_counts_modes_and_keeps_gate_closed():
    sources = [
        {"id": "v0", "source_status": "active", "import_state": "catalogued", "text_mode": "vision_required", "imported_record_count": 0},
        {"id": "v1", "source_status": "active", "import_state": "catalogued", "text_mode": "vision_required", "imported_record_count": 2},
        {"id": "m0", "source_status": "active", "import_state": "catalogued", "text_mode": "mixed", "imported_record_count": None},
        {"id": "text", "source_status": "active", "import_state": "catalogued", "text_mode": "text", "imported_record_count": 10},
        {"id": "inactive", "source_status": "superseded", "import_state": "catalogued", "text_mode": "vision_required", "imported_record_count": 5},
    ]

    result = summarize_vision_import_coverage(sources)

    assert result["active_catalogued_vision_or_mixed_sources"] == 3
    assert result["sources_with_imported_records"] == 1
    assert result["sources_with_zero_imported_records"] == 2
    assert result["coverage_percent"] == 33.33
    assert result["by_text_mode"] == {
        "mixed": {"sources": 1, "with_imported_records": 0, "zero_imported_records": 1},
        "vision_required": {"sources": 2, "with_imported_records": 1, "zero_imported_records": 1},
    }
    assert result["source_ids_with_imported_records"] == ["v1"]
    assert result["source_ids_with_zero_imported_records"] == ["m0", "v0"]
    assert result["parser_ocr_coverage_gate_clear"] is False
    assert result["registry_import_count_is_coverage_evidence_only"] is True
    assert result["ocr_authorized"] is False
    assert result["external_processing_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_vision_import_coverage_normalizes_registry_metadata():
    result = summarize_vision_import_coverage([
        {"id": "done", "source_status": " ACTIVE ", "import_state": " Catalogued ", "text_mode": " Mixed ", "imported_record_count": 1}
    ])

    assert result["active_catalogued_vision_or_mixed_sources"] == 1
    assert result["sources_with_imported_records"] == 1
    assert result["coverage_percent"] == 100.0
    assert result["parser_ocr_coverage_gate_clear"] is True


def test_vision_import_coverage_empty_scope_is_not_falsely_blocked():
    result = summarize_vision_import_coverage([])

    assert result["active_catalogued_vision_or_mixed_sources"] == 0
    assert result["coverage_percent"] is None
    assert result["parser_ocr_coverage_gate_clear"] is True
