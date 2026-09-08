from scripts.audit_zero_import_structured_artifacts import (
    summarize_zero_import_structured_artifacts,
)


def _source(source_id: str, filename: str, pages: int) -> dict:
    return {
        "id": source_id,
        "source_status": "active",
        "import_state": "catalogued",
        "text_mode": "vision_required",
        "imported_record_count": 0,
        "physical_filename": filename,
        "physical_pages": pages,
    }


def test_structured_artifact_audit_is_conservative():
    sources = [
        _source("exact", "Book_1787000000000.pdf", 120),
        _source("name-only", "Other.pdf", 80),
        _source("absent", "Missing.pdf", 30),
        _source("ambiguous", "Dup.pdf", 50),
        {
            **_source("ignored-imported", "Imported.pdf", 20),
            "imported_record_count": 3,
        },
    ]
    analyses = [
        {"filename": "Book.pdf", "pages": 120, "total_characters": 5000},
        {"filename": "Other.pdf", "pages": 79, "total_characters": 0},
        {"filename": "Dup.pdf", "pages": 50, "total_characters": 10},
        {"filename": "Dup_1787000000000.pdf", "pages": 50, "total_characters": 10},
        {"filename": "Imported.pdf", "pages": 20, "total_characters": 100},
    ]

    result = summarize_zero_import_structured_artifacts(sources, analyses)

    assert result["zero_import_vision_sources_total"] == 4
    assert result["zero_import_sources_with_filename_and_page_count_artifact_evidence"] == 1
    assert result["zero_import_sources_with_filename_only_artifact_evidence"] == 1
    assert result["zero_import_sources_with_ambiguous_artifact_evidence"] == 1
    assert result["zero_import_sources_without_structured_artifact_evidence"] == 1
    assert result["zero_import_sources_with_historical_extracted_text"] == 1
    assert result["zero_import_sources_with_historical_zero_text"] == 1
    assert result["zero_import_sources_with_exact_historical_text_review_evidence"] == 1
    assert result["zero_import_sources_with_inconclusive_structured_artifact_evidence"] == 1
    assert result["source_ids_with_filename_and_page_count_artifact_evidence"] == ["exact"]
    assert result["source_ids_with_filename_only_artifact_evidence"] == ["name-only"]
    assert result["source_ids_with_ambiguous_artifact_evidence"] == ["ambiguous"]
    assert result["source_ids_without_structured_artifact_evidence"] == ["absent"]
    assert result["source_ids_with_exact_historical_text_review_evidence"] == ["exact"]
    assert result["source_ids_with_inconclusive_structured_artifact_evidence"] == [
        "name-only"
    ]
    assert result["historical_evidence_triage_partition_complete"] is True
    assert result["historical_artifact_evidence_is_diagnostic_only"] is True
    assert result["historical_extracted_text_requires_manual_review"] is True
    assert result["historical_extracted_text_does_not_authorize_import"] is True
    assert result["ocr_authorized"] is False
    assert result["external_processing_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False
