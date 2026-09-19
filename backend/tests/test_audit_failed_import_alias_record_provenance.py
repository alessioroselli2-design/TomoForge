from scripts.audit_failed_import_alias_record_provenance import (
    summarize_failed_alias_record_provenance,
)


def _job(filename: str, language: str = "it") -> dict:
    return {
        "id": f"job-{filename}",
        "filename": filename,
        "source_language": language,
        "source_fingerprint": "job-sha",
        "status": "failed",
        "last_error": "manual_source_missing",
    }


def _source(filename: str, logical_source_id: str, language: str = "it") -> dict:
    return {
        "id": f"src-{logical_source_id}",
        "physical_filename": filename,
        "physical_sha256": "registry-sha",
        "logical_source_id": logical_source_id,
        "language": language,
    }


def test_historical_records_are_split_between_exclusive_and_mixed_provenance():
    job_filename = "Bardo__1787233073462.pdf"
    jobs = [_job(job_filename)]
    sources = [_source("Bardo .pdf", "derived_class_bardo")]
    records = [
        {
            "source_key": job_filename,
            "source_language": "it",
            "source_refs": [{"page": 1, "filename": job_filename}],
        },
        {
            "source_key": job_filename,
            "source_language": "it",
            "source_refs": [
                {"page": 3, "filename": job_filename},
                {"page": 5, "filename": "Mago__1787233073462.pdf"},
            ],
        },
        {
            "source_key": job_filename,
            "source_language": "it",
            "source_refs": [{"page": 7, "filename": "Other.pdf"}],
        },
    ]

    result = summarize_failed_alias_record_provenance(jobs, sources, records)

    assert result["review_only_alias_candidates"] == 1
    assert result["historical_records_total"] == 3
    assert result["records_with_job_filename_in_source_refs"] == 2
    assert result["records_exclusive_to_job_filename"] == 1
    assert result["records_with_mixed_file_provenance"] == 1
    assert result["records_missing_job_filename_in_source_refs"] == 1
    candidate = result["candidates"][0]
    assert candidate["logical_source_id"] == "derived_class_bardo"
    assert candidate["records_matching_job_language"] == 3
    assert candidate["hash_confirmed"] is False
    assert candidate["requires_manual_reconciliation"] is True
    assert result["record_link_is_exact_source_key_only"] is True
    assert result["registry_identity_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["translation_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_exact_hash_match_is_not_an_unconfirmed_alias_candidate():
    job_filename = "Book_1787286581630.pdf"
    jobs = [{**_job(job_filename), "source_fingerprint": "same-sha"}]
    sources = [
        {
            **_source("Book.pdf", "book_it"),
            "physical_sha256": "same-sha",
        }
    ]
    records = [
        {
            "source_key": job_filename,
            "source_language": "it",
            "source_refs": [{"page": 1, "filename": job_filename}],
        }
    ]

    result = summarize_failed_alias_record_provenance(jobs, sources, records)

    assert result["review_only_alias_candidates"] == 0
    assert result["historical_records_total"] == 0
    assert result["candidates"] == []


def test_non_failed_or_ambiguous_alias_jobs_are_ignored():
    filename = "Book_1787286581630.pdf"
    jobs = [
        {**_job(filename), "status": "completed"},
        _job("Ambiguous_1787286581630.pdf"),
    ]
    sources = [
        _source("Ambiguous(1).pdf", "a"),
        _source("Ambiguous(2).pdf", "b"),
    ]

    result = summarize_failed_alias_record_provenance(jobs, sources, [])

    assert result["review_only_alias_candidates"] == 0
    assert result["automatic_retry_authorized"] is False
