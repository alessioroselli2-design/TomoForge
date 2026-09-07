from scripts.audit_schema_cache_external_ocr_evidence import summarize_external_ocr_evidence


def _schema_cache_job(**overrides):
    job = {
        "filename": "Manuale_del_giocatore__1787259882002.pdf",
        "status": "failed",
        "page_count": 321,
        "current_page": 61,
        "records_imported": 10,
        "records_updated": 0,
        "records_flagged": 0,
        "last_error": {
            "message": "Could not find the 'level' column of 'private_reference_records' in the schema cache",
            "code": "PGRST204",
        },
        "external_processing_confirmed": True,
        "pages_needing_ocr": [],
    }
    job.update(overrides)
    return job


def test_confirmation_and_backlog_are_not_artifact_evidence():
    result = summarize_external_ocr_evidence(
        [_schema_cache_job(pages_needing_ocr=[12, 13, 14])]
    )

    assert result["schema_cache_failures_with_record_activity"] == 1
    assert result["jobs_with_external_processing_confirmed"] == 1
    assert result["explicit_external_artifact_locator_candidates"] == 0
    assert result["validated_external_ocr_artifacts"] == 0
    assert result["external_object_store_checked"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False
    assert result["jobs"][0]["pages_needing_ocr_entries"] == 3
    assert result["jobs"][0]["external_processing_confirmation_counts_as_artifact_evidence"] is False
    assert result["jobs"][0]["ocr_backlog_marker_counts_as_artifact_evidence"] is False


def test_explicit_locator_is_only_a_candidate_until_store_is_verified():
    result = summarize_external_ocr_evidence(
        [
            _schema_cache_job(
                pages_needing_ocr=[
                    {"page": 12, "r2_key": "ocr/manual/page-012.ocr.json"},
                    {"page": 13, "nested": {"text_url": "https://example.invalid/page-013.ocr.txt"}},
                ]
            )
        ]
    )

    assert result["explicit_external_artifact_locator_candidates"] == 2
    assert result["validated_external_ocr_artifacts"] == 0
    assert result["external_object_store_checked"] is False
    assert result["record_set_completeness_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["ocr_executed"] is False


def test_non_schema_cache_failure_is_excluded():
    result = summarize_external_ocr_evidence(
        [_schema_cache_job(last_error="manual_source_missing")]
    )

    assert result["schema_cache_failures_with_record_activity"] == 0
