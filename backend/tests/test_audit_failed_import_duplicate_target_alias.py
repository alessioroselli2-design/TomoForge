from scripts.audit_failed_import_source_provenance import summarize_failed_import_source_provenance


def test_duplicate_target_alias_conflict_stays_diagnostic_and_review_only():
    sources = [
        {
            "physical_filename": "847921086-Manuale-Dei-Mostri-5e.pdf",
            "physical_sha256": "registry-mm-sha",
            "logical_source_id": "mm_2014_it",
        },
        {
            "physical_filename": "Manuale del giocatore .pdf",
            "physical_sha256": "registry-phb-sha",
            "logical_source_id": "phb_2014_it",
        },
    ]
    jobs = [
        {
            "filename": "847921086-Manuale-Dei-Mostri-5e_ok_1787286581630.pdf",
            "source_fingerprint": "job-mm-sha",
            "status": "failed",
            "last_error": "manual_source_duplicate:Manuale_del_giocatore__1787259882002.pdf",
        }
    ]

    result = summarize_failed_import_source_provenance(sources, jobs)

    assert result["reported_duplicate_targets_present_in_registry"] == 0
    assert result["reported_duplicate_target_alias_candidates"] == 1
    assert result["reported_duplicate_target_alias_conflicts_with_job_alias"] == 1
    assert result["duplicate_target_alias_evidence_is_diagnostic_only"] is True
    assert result["requires_manual_reconciliation"] == 1
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_generation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_same_alias_duplicate_target_is_not_reported_as_cross_source_conflict():
    sources = [
        {
            "physical_filename": "Manuale del giocatore .pdf",
            "physical_sha256": "registry-phb-sha",
            "logical_source_id": "phb_2014_it",
        }
    ]
    jobs = [
        {
            "filename": "Manuale_del_giocatore__1787259882002.pdf",
            "source_fingerprint": "job-phb-sha",
            "status": "failed",
            "last_error": "manual_source_duplicate:Manuale_del_giocatore__1787259882002.pdf",
        }
    ]

    result = summarize_failed_import_source_provenance(sources, jobs)

    assert result["reported_duplicate_target_alias_candidates"] == 1
    assert result["reported_duplicate_target_alias_conflicts_with_job_alias"] == 0
    assert result["automatic_retry_authorized"] is False
