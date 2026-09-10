from scripts.audit_verified_authority_shared_spells import summarize_verified_authority_shared_spell_evidence


def _fixture(authority_review_status="verified"):
    owner = "Bardo__1787233073462.pdf"
    companion = "Stregone__1787233073462.pdf"
    jobs = [{
        "id": "job-bardo",
        "filename": owner,
        "status": "failed",
        "last_error": "manual_source_missing",
        "source_fingerprint": "job-sha",
    }]
    sources = [
        {
            "physical_filename": "Bardo .pdf",
            "physical_sha256": "registry-sha",
            "logical_source_id": "derived_class_bardo",
            "source_role": "extraction_aid",
            "source_status": "active",
        },
        {
            "physical_filename": "Manuale_del_Giocatore.pdf",
            "physical_sha256": "phb-sha",
            "logical_source_id": "phb-it",
            "source_role": "authority",
            "source_status": "active",
        },
    ]
    records = [
        {
            "source_key": owner,
            "reference_type": "spell",
            "normalized_name": "cura ferite",
            "source_refs": [{"filename": owner}, {"filename": companion}],
            "review_status": "needs_review",
        },
        {
            "source_key": companion,
            "reference_type": "spell",
            "normalized_name": "cura ferite",
            "source_refs": [{"filename": companion}],
            "review_status": "needs_review",
        },
        {
            "source_key": "Manuale_del_Giocatore.pdf",
            "reference_type": "spell",
            "normalized_name": "cura ferite",
            "source_refs": [{"filename": "Manuale_del_Giocatore.pdf"}],
            "review_status": authority_review_status,
        },
    ]
    return jobs, sources, records


def test_verified_active_authority_identity_is_stronger_support_only():
    jobs, sources, records = _fixture("verified")
    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    assert result["shared_class_card_candidate_pairs"] == 1
    assert result["shared_class_card_candidate_pairs_with_verified_active_authority_identity_evidence"] == 1
    assert result["shared_class_card_candidate_pairs_without_verified_active_authority_identity_evidence"] == 0
    assert result["verified_active_authority_structured_identities"] == 1
    assert result["verified_authority_identity_evidence_is_confirmation"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False

    pair = result["unidirectional_pairs"][0]
    assert pair["mixed_records_with_verified_active_authority_same_identity"] == 1
    assert pair["verified_active_authority_same_identity_is_stronger_supporting_evidence"] is True
    assert pair["identity_confirmed"] is False
    assert pair["requires_manual_reconciliation"] is True


def test_needs_review_authority_record_does_not_count_as_verified_evidence():
    jobs, sources, records = _fixture("needs_review")
    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    assert result["verified_active_authority_structured_identities"] == 0
    assert result["shared_class_card_candidate_pairs_with_verified_active_authority_identity_evidence"] == 0
    assert result["shared_class_card_candidate_pairs_without_verified_active_authority_identity_evidence"] == 1
    pair = result["unidirectional_pairs"][0]
    assert pair["mixed_records_with_verified_active_authority_same_identity"] == 0
    assert pair["verified_active_authority_same_identity_is_stronger_supporting_evidence"] is False


def test_pending_authority_record_does_not_count_as_verified_evidence():
    jobs, sources, records = _fixture("pending")
    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    assert result["verified_active_authority_structured_identities"] == 0
    assert result["shared_class_card_candidate_pairs_with_verified_active_authority_identity_evidence"] == 0
    assert result["shared_class_card_candidate_pairs_without_verified_active_authority_identity_evidence"] == 1
