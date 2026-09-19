from scripts.audit_failed_import_alias_mixed_contributors import (
    summarize_failed_alias_mixed_contributors,
)


def _job(filename: str) -> dict:
    return {
        "id": f"job-{filename}",
        "filename": filename,
        "source_fingerprint": "job-sha",
        "status": "failed",
        "last_error": "manual_source_missing",
    }


def _source(filename: str, logical_source_id: str) -> dict:
    return {
        "id": f"src-{logical_source_id}",
        "physical_filename": filename,
        "physical_sha256": "registry-sha",
        "logical_source_id": logical_source_id,
    }


def test_companion_files_are_counted_once_per_mixed_record():
    filename = "Bardo__1787233073462.pdf"
    jobs = [_job(filename)]
    sources = [_source("Bardo .pdf", "derived_class_bardo")]
    records = [
        {
            "source_key": filename,
            "source_refs": [
                {"page": 1, "filename": filename},
                {"page": 2, "filename": "Mago__1787233073462.pdf"},
                {"page": 3, "filename": "Mago__1787233073462.pdf"},
                {"page": 4, "filename": "Stregone__1787233073462.pdf"},
            ],
        },
        {
            "source_key": filename,
            "source_refs": [
                {"page": 5, "filename": filename},
                {"page": 6, "filename": "Mago__1787233073462.pdf"},
            ],
        },
        {
            "source_key": filename,
            "source_refs": [{"page": 7, "filename": filename}],
        },
    ]

    result = summarize_failed_alias_mixed_contributors(jobs, sources, records)

    assert result["review_only_alias_candidates"] == 1
    assert result["mixed_provenance_records_total"] == 2
    candidate = result["candidates"][0]
    assert candidate["historical_records"] == 3
    assert candidate["mixed_provenance_records"] == 2
    assert candidate["distinct_companion_files"] == 2
    assert candidate["companion_files"] == [
        {"filename": "Mago__1787233073462.pdf", "record_count": 2},
        {"filename": "Stregone__1787233073462.pdf", "record_count": 1},
    ]
    assert candidate["hash_confirmed"] is False
    assert candidate["requires_manual_reconciliation"] is True
    assert result["record_link_is_exact_source_key_only"] is True
    assert result["companion_counts_are_per_record"] is True
    assert result["registry_identity_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["translation_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_exact_hash_match_and_ambiguous_alias_are_not_review_candidates():
    exact = "Book_1787286581630.pdf"
    ambiguous = "Ambiguous_1787286581630.pdf"
    jobs = [
        {**_job(exact), "source_fingerprint": "same-sha"},
        _job(ambiguous),
    ]
    sources = [
        {**_source("Book.pdf", "book_it"), "physical_sha256": "same-sha"},
        _source("Ambiguous(1).pdf", "ambiguous_a"),
        _source("Ambiguous(2).pdf", "ambiguous_b"),
    ]

    result = summarize_failed_alias_mixed_contributors(jobs, sources, [])

    assert result["review_only_alias_candidates"] == 0
    assert result["mixed_provenance_records_total"] == 0
    assert result["candidates"] == []
