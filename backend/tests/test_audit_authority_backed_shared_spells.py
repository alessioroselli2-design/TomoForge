from scripts.audit_authority_backed_shared_spells import summarize_authority_backed_shared_spell_evidence


def _fixture():
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
    return jobs, sources, records


def test_active_authority_identity_is_support_only():
    jobs, sources, records = _fixture()
    result = summarize_authority_backed_shared_spell_evidence(jobs, sources, records)

    assert result["shared_class_card_candidate_pairs"] == 1
    assert result["shared_class_card_candidate_pairs_with_active_authority_identity_evidence"] == 1
    assert result["active_authority_registry_filenames"] == 1
    assert result["authority_identity_evidence_is_confirmation"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False

    pair = result["unidirectional_pairs"][0]
    assert pair["mixed_records_with_active_authority_same_identity"] == 1
    assert pair["active_authority_same_identity_is_supporting_evidence"] is True
    assert pair["identity_confirmed"] is False
    assert pair["requires_manual_reconciliation"] is True


def test_extraction_aid_does_not_count_as_authority():
    jobs, sources, records = _fixture()
    sources[1]["source_role"] = "extraction_aid"

    result = summarize_authority_backed_shared_spell_evidence(jobs, sources, records)

    assert result["active_authority_registry_filenames"] == 0
    assert result["shared_class_card_candidate_pairs_with_active_authority_identity_evidence"] == 0
    pair = result["unidirectional_pairs"][0]
    assert pair["mixed_records_with_active_authority_same_identity"] == 0
    assert pair["active_authority_same_identity_is_supporting_evidence"] is False


def test_superseded_authority_does_not_count_as_active_authority():
    jobs, sources, records = _fixture()
    sources[1]["source_status"] = "superseded"

    result = summarize_authority_backed_shared_spell_evidence(jobs, sources, records)

    assert result["active_authority_registry_filenames"] == 0
    assert result["shared_class_card_candidate_pairs_with_active_authority_identity_evidence"] == 0
