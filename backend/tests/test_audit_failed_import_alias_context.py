from scripts.audit_failed_import_alias_context import summarize_failed_import_alias_context


def test_alias_context_is_review_only_even_when_language_pages_and_activity_match():
    jobs = [
        {
            "id": "job-bardo",
            "filename": "Bardo__1787233073462.pdf",
            "source_language": "it",
            "source_fingerprint": "job-sha",
            "page_count": 26,
            "status": "failed",
            "last_error": "manual_source_missing",
            "records_imported": 7,
            "records_updated": 100,
            "records_flagged": 0,
            "records_skipped": 0,
        }
    ]
    sources = [
        {
            "id": "src-bardo",
            "physical_filename": "Bardo .pdf",
            "physical_sha256": "registry-sha",
            "physical_pages": 26,
            "logical_source_id": "derived_class_bardo",
            "language": "it",
        }
    ]

    result = summarize_failed_import_alias_context(jobs, sources)

    assert result["review_only_alias_candidates"] == 1
    assert result["alias_candidates_with_language_match"] == 1
    assert result["alias_candidates_with_page_count_match"] == 1
    assert result["alias_candidates_with_prior_record_activity"] == 1
    assert result["alias_candidate_logical_source_ids"] == ["derived_class_bardo"]
    candidate = result["candidates"][0]
    assert candidate["hash_confirmed"] is False
    assert candidate["requires_manual_reconciliation"] is True
    assert result["registry_identity_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["translation_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_language_or_page_disagreement_remains_visible_and_non_actionable():
    jobs = [
        {
            "id": "job-phb",
            "filename": "Manual_1787286581630.pdf",
            "source_language": "es",
            "source_fingerprint": "job-sha",
            "page_count": 100,
            "status": "failed",
            "last_error": "manual_source_missing",
            "records_imported": 0,
            "records_updated": 0,
            "records_flagged": 0,
            "records_skipped": 0,
        }
    ]
    sources = [
        {
            "id": "src-phb",
            "physical_filename": "Manual(1).pdf",
            "physical_sha256": "registry-sha",
            "physical_pages": 101,
            "logical_source_id": "phb_2014_it",
            "language": "it",
        }
    ]

    result = summarize_failed_import_alias_context(jobs, sources)

    assert result["review_only_alias_candidates"] == 1
    assert result["alias_candidates_with_language_match"] == 0
    assert result["alias_candidates_with_page_count_match"] == 0
    assert result["alias_candidates_with_prior_record_activity"] == 0
    assert result["automatic_retry_authorized"] is False


def test_exact_hash_confirmation_is_not_reported_as_unconfirmed_alias_candidate():
    jobs = [
        {
            "id": "job-exact",
            "filename": "Book_1787286581630.pdf",
            "source_language": "it",
            "source_fingerprint": "same-sha",
            "page_count": 20,
            "status": "failed",
            "last_error": "manual_source_missing",
        }
    ]
    sources = [
        {
            "id": "src-exact",
            "physical_filename": "Book.pdf",
            "physical_sha256": "same-sha",
            "physical_pages": 20,
            "logical_source_id": "book_it",
            "language": "it",
        }
    ]

    result = summarize_failed_import_alias_context(jobs, sources)

    assert result["review_only_alias_candidates"] == 0
    assert result["candidates"] == []
    assert result["registry_identity_confirmed"] is False


def test_ambiguous_aliases_are_not_promoted_to_context_candidates():
    jobs = [
        {
            "id": "job-ambiguous",
            "filename": "Book_1787286581630.pdf",
            "source_fingerprint": "job-sha",
            "status": "failed",
            "last_error": "manual_source_missing",
        }
    ]
    sources = [
        {"id": "a", "physical_filename": "Book(1).pdf", "physical_sha256": "a"},
        {"id": "b", "physical_filename": "Book(2).pdf", "physical_sha256": "b"},
    ]

    result = summarize_failed_import_alias_context(jobs, sources)

    assert result["review_only_alias_candidates"] == 0
    assert result["automatic_retry_authorized"] is False
