from scripts.audit_unidirectional_alias_identity_evidence import summarize_unidirectional_identity_evidence


def test_one_way_companion_stays_review_only_and_reports_identity_evidence():
    owner = "Bardo__1787233073462.pdf"
    companion = "Stregone__1787233073462.pdf"
    jobs = [{
        "id": "job-bardo",
        "filename": owner,
        "status": "failed",
        "last_error": "manual_source_missing",
        "source_fingerprint": "job-sha",
    }]
    sources = [{
        "physical_filename": "Bardo .pdf",
        "physical_sha256": "registry-sha",
        "logical_source_id": "derived_class_bardo",
    }]
    records = [
        {
            "source_key": owner,
            "reference_type": "other",
            "normalized_name": "messaggio",
            "source_refs": [{"filename": owner}, {"filename": companion}],
        },
        {
            "source_key": owner,
            "reference_type": "other",
            "normalized_name": "cecita sordita",
            "source_refs": [{"filename": owner}, {"filename": companion}],
        },
        {
            "source_key": companion,
            "reference_type": "other",
            "normalized_name": "messaggio",
            "source_refs": [{"filename": companion}],
        },
    ]

    result = summarize_unidirectional_identity_evidence(jobs, sources, records)

    assert result["one_way_provenance_confirms_identity"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False
    assert len(result["unidirectional_pairs"]) == 1
    pair = result["unidirectional_pairs"][0]
    assert pair["companion_filename"] == companion
    assert pair["mixed_records"] == 2
    assert pair["companion_owned_records"] == 1
    assert pair["mixed_records_with_companion_owned_same_identity"] == 1
    assert pair["mixed_records_without_companion_owned_same_identity"] == 1
    assert pair["identity_confirmed"] is False
    assert pair["requires_manual_reconciliation"] is True


def test_reciprocal_companion_is_not_reported_as_one_way():
    owner = "Bardo__1787233073462.pdf"
    companion = "Mago__1787233073462.pdf"
    jobs = [{"id": "j", "filename": owner, "status": "failed", "last_error": "manual_source_missing", "source_fingerprint": "a"}]
    sources = [{"physical_filename": "Bardo .pdf", "physical_sha256": "b", "logical_source_id": "derived_class_bardo"}]
    records = [
        {"source_key": owner, "reference_type": "other", "normalized_name": "x", "source_refs": [{"filename": owner}, {"filename": companion}]},
        {"source_key": companion, "reference_type": "other", "normalized_name": "x", "source_refs": [{"filename": companion}, {"filename": owner}]},
    ]

    result = summarize_unidirectional_identity_evidence(jobs, sources, records)
    assert result["unidirectional_pairs"] == []
