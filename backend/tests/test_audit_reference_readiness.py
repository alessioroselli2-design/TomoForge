from scripts.audit_reference_readiness import summarize_readiness


def test_summarize_readiness_reports_only_aggregate_state():
    records = [
        {"review_status": "verified", "translation_status": "not_required", "canonical_id": None, "name": "Private rule text"},
        {"review_status": "needs_review", "translation_status": "failed", "canonical_id": "canon-1", "full_text": "Sensitive source text"},
        {"review_status": "pending", "translation_status": "translated", "canonical_id": ""},
    ]
    sources = [
        {"source_status": "active", "text_mode": "text", "import_state": "catalogued", "physical_filename": "private.pdf"},
        {"source_status": "duplicate", "text_mode": "vision_required", "import_state": "excluded"},
        {"source_status": "superseded", "text_mode": "mixed", "import_state": "catalogued"},
    ]
    canonical = [
        {"verification_status": "verified", "full_text": "canonical private text"},
        {"verification_status": "needs_review"},
    ]

    result = summarize_readiness(records, sources, canonical)

    assert result == {
        "records_total": 3,
        "records_verified": 1,
        "records_needs_review": 1,
        "records_pending": 1,
        "translation_failed": 1,
        "translation_translated": 1,
        "records_linked_to_canonical": 1,
        "verified_ratio": 0.3333,
        "sources_total": 3,
        "sources_active": 1,
        "sources_duplicate": 1,
        "sources_superseded": 1,
        "sources_catalogued": 2,
        "sources_excluded": 1,
        "sources_text": 1,
        "sources_mixed": 1,
        "sources_vision_required": 1,
        "canonical_total": 2,
        "canonical_verified": 1,
        "canonical_needs_review": 1,
    }
    rendered = str(result)
    assert "Private rule text" not in rendered
    assert "Sensitive source text" not in rendered
    assert "private.pdf" not in rendered
    assert "canonical private text" not in rendered


def test_summarize_readiness_handles_empty_catalogue():
    result = summarize_readiness([], [], [])
    assert result["records_total"] == 0
    assert result["verified_ratio"] == 0.0
    assert result["canonical_total"] == 0
