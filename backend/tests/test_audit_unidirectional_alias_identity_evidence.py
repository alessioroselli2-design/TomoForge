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
    assert result["shared_class_card_candidate_pairs"] == 1
    assert result["shared_class_card_candidate_pairs_with_non_class_identity_evidence"] == 0
    assert result["shared_class_card_candidate_is_confirmation"] is False
    assert result["non_class_identity_evidence_is_confirmation"] is False
    assert len(result["unidirectional_pairs"]) == 1
    pair = result["unidirectional_pairs"][0]
    assert pair["companion_filename"] == companion
    assert pair["mixed_records"] == 2
    assert pair["companion_owned_records"] == 1
    assert pair["mixed_records_with_companion_owned_same_identity"] == 1
    assert pair["mixed_records_without_companion_owned_same_identity"] == 1
    assert pair["mixed_records_with_non_class_same_identity"] == 0
    assert pair["mixed_records_without_non_class_same_identity"] == 2
    assert pair["non_class_same_identity_is_supporting_evidence"] is False
    assert pair["shared_class_card_candidate"] is True
    assert pair["owner_class_pack"] == "bardo"
    assert pair["companion_class_pack"] == "stregone"
    assert pair["identity_confirmed"] is False
    assert pair["requires_manual_reconciliation"] is True


def test_shared_class_pair_reports_matching_non_class_reference_as_support_only():
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
            "reference_type": "spell",
            "normalized_name": "cura ferite",
            "source_refs": [{"filename": owner}, {"filename": companion}],
        },
        {
            "source_key": companion,
            "reference_type": "spell",
            "normalized_name": "cura ferite",
            "source_refs": [{"filename": companion}],
        },
        {
            "source_key": "Manuale_del_Giocatore.pdf",
            "reference_type": "spell",
            "normalized_name": "cura ferite",
            "source_refs": [{"filename": "Manuale_del_Giocatore.pdf"}],
        },
    ]

    result = summarize_unidirectional_identity_evidence(jobs, sources, records)

    assert result["shared_class_card_candidate_pairs"] == 1
    assert result["shared_class_card_candidate_pairs_with_non_class_identity_evidence"] == 1
    assert result["non_class_identity_evidence_is_confirmation"] is False
    pair = result["unidirectional_pairs"][0]
    assert pair["shared_class_card_candidate"] is True
    assert pair["mixed_records_with_non_class_same_identity"] == 1
    assert pair["mixed_records_without_non_class_same_identity"] == 0
    assert pair["non_class_same_identity_is_supporting_evidence"] is True
    assert pair["identity_confirmed"] is False
    assert pair["requires_manual_reconciliation"] is True


def test_non_class_companion_is_not_marked_as_shared_class_card_candidate():
    owner = "Bardo__1787233073462.pdf"
    companion = "Manuale_del_Giocatore.pdf"
    jobs = [{"id": "j", "filename": owner, "status": "failed", "last_error": "manual_source_missing", "source_fingerprint": "a"}]
    sources = [{"physical_filename": "Bardo .pdf", "physical_sha256": "b", "logical_source_id": "derived_class_bardo"}]
    records = [
        {"source_key": owner, "reference_type": "other", "normalized_name": "x", "source_refs": [{"filename": owner}, {"filename": companion}]},
    ]

    result = summarize_unidirectional_identity_evidence(jobs, sources, records)
    pair = result["unidirectional_pairs"][0]
    assert pair["shared_class_card_candidate"] is False
    assert pair["owner_class_pack"] == "bardo"
    assert pair["companion_class_pack"] is None
    assert result["shared_class_card_candidate_pairs"] == 0


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
    assert result["shared_class_card_candidate_pairs"] == 0
