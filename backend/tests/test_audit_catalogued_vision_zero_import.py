from scripts.audit_catalogued_vision_zero_import import summarize_catalogued_vision_zero_import


def test_catalogued_vision_zero_import_gate_is_conservative():
    sources = [
        {
            "id": "blocked-vision",
            "source_status": "active",
            "import_state": "catalogued",
            "text_mode": "vision_required",
            "imported_record_count": 0,
        },
        {
            "id": "blocked-mixed",
            "source_status": "active",
            "import_state": "catalogued",
            "text_mode": "mixed",
            "imported_record_count": None,
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

    result = summarize_catalogued_vision_zero_import(sources)

    assert result["active_catalogued_vision_sources_examined"] == 3
    assert result["active_catalogued_vision_sources_with_zero_imported_records"] == 2
    assert result["blocked_source_ids"] == ["blocked-mixed", "blocked-vision"]
    assert result["requires_authorized_text_extraction_before_import"] is True
    assert result["evidence_is_diagnostic_only"] is True
    assert result["ocr_authorized"] is False
    assert result["external_processing_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


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
    assert result["requires_authorized_text_extraction_before_import"] is False
