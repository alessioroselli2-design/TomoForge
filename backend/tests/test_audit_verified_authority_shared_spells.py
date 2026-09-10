from scripts.audit_verified_authority_shared_spells import (
    AMBIGUOUS_REVIEW,
    AUTHORITATIVE_UNVERIFIED,
    AUTHORITATIVE_VERIFIED,
    CLASS_SOURCES_ONLY,
    summarize_verified_authority_shared_spell_evidence,
)


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
    assert result["residual_shared_class_card_candidate_pairs"] == []
    assert result["residual_shared_class_card_candidate_pairs_by_reason"] == {}
    assert result["active_authority_structured_identities"] == 1
    assert result["verified_active_authority_structured_identities"] == 1
    assert result["shared_class_card_candidate_pairs_by_evidence_classification"] == {
        AUTHORITATIVE_VERIFIED: 1
    }
    assert result["verified_authority_identity_evidence_is_confirmation"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False

    pair = result["unidirectional_pairs"][0]
    assert pair["mixed_records_with_active_authority_same_identity"] == 1
    assert pair["mixed_records_with_verified_active_authority_same_identity"] == 1
    assert pair["verified_active_authority_same_identity_is_stronger_supporting_evidence"] is True
    assert pair["shared_spell_evidence_classification"] == AUTHORITATIVE_VERIFIED
    assert pair["classification_requires_review"] is False
    assert pair["residual_review_reason"] is None
    assert pair["identity_confirmed"] is False
    assert pair["requires_manual_reconciliation"] is True


def test_needs_review_authority_record_does_not_count_as_verified_evidence():
    jobs, sources, records = _fixture("needs_review")
    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    assert result["active_authority_structured_identities"] == 1
    assert result["verified_active_authority_structured_identities"] == 0
    assert result["shared_class_card_candidate_pairs_with_verified_active_authority_identity_evidence"] == 0
    assert result["shared_class_card_candidate_pairs_without_verified_active_authority_identity_evidence"] == 1
    assert result["shared_class_card_candidate_pairs_by_evidence_classification"] == {
        AUTHORITATIVE_UNVERIFIED: 1
    }
    assert result["residual_shared_class_card_candidate_pairs_by_reason"] == {
        "active_authority_identity_present_but_not_verified": 1
    }
    assert len(result["residual_shared_class_card_candidate_pairs"]) == 1
    pair = result["unidirectional_pairs"][0]
    assert pair["shared_spell_evidence_classification"] == AUTHORITATIVE_UNVERIFIED
    assert pair["classification_requires_review"] is False
    assert pair["requires_manual_reconciliation"] is True


def test_pending_authority_record_does_not_count_as_verified_evidence():
    jobs, sources, records = _fixture("pending")
    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    assert result["active_authority_structured_identities"] == 1
    assert result["verified_active_authority_structured_identities"] == 0
    assert result["shared_class_card_candidate_pairs_with_verified_active_authority_identity_evidence"] == 0
    assert result["shared_class_card_candidate_pairs_without_verified_active_authority_identity_evidence"] == 1
    assert result["shared_class_card_candidate_pairs_by_evidence_classification"] == {
        AUTHORITATIVE_UNVERIFIED: 1
    }


def test_class_sources_only_requires_only_class_alias_provenance():
    jobs, sources, records = _fixture("needs_review")
    records[-1]["normalized_name"] = "dardo di fuoco"
    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    pair = result["unidirectional_pairs"][0]
    assert pair["shared_spell_evidence_classification"] == CLASS_SOURCES_ONLY
    assert pair["classification_requires_review"] is False
    assert pair["residual_review_reason"] == "no_active_authority_same_identity"


def test_class_plus_extraction_aid_is_ambiguous():
    jobs, sources, records = _fixture("needs_review")
    records[-1]["normalized_name"] = "dardo di fuoco"
    records[0]["source_refs"].append({"filename": "Bardo .pdf"})
    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    pair = result["unidirectional_pairs"][0]
    assert pair["shared_spell_evidence_classification"] == AMBIGUOUS_REVIEW
    assert pair["classification_requires_review"] is True
    assert len(result["shared_class_card_candidate_pairs_requiring_classification_review"]) == 1


def test_class_plus_superseded_authority_is_ambiguous():
    jobs, sources, records = _fixture("needs_review")
    records[-1]["normalized_name"] = "dardo di fuoco"
    sources.append({
        "physical_filename": "Vecchio_Manuale.pdf",
        "source_role": "authority",
        "source_status": "superseded",
    })
    records[0]["source_refs"].append({"filename": "Vecchio_Manuale.pdf"})
    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    pair = result["unidirectional_pairs"][0]
    assert pair["shared_spell_evidence_classification"] == AMBIGUOUS_REVIEW
    assert pair["classification_requires_review"] is True


def test_missing_identity_is_ambiguous_even_with_class_aliases():
    jobs, sources, records = _fixture("needs_review")
    records[-1]["normalized_name"] = "dardo di fuoco"
    records[0]["normalized_name"] = ""
    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    pair = result["unidirectional_pairs"][0]
    assert pair["shared_spell_evidence_classification"] == AMBIGUOUS_REVIEW
    assert pair["classification_requires_review"] is True


def _add_same_identity_non_class_record(sources, records, *, filename, role, status="active"):
    sources.append({
        "physical_filename": filename,
        "physical_sha256": f"sha-{filename}",
        "logical_source_id": f"source-{filename}",
        "source_role": role,
        "source_status": status,
    })
    records.append({
        "source_key": filename,
        "reference_type": "spell",
        "normalized_name": "cura ferite",
        "source_refs": [{"filename": filename}],
        "review_status": "needs_review",
    })


def test_separate_same_identity_extraction_aid_keeps_pair_ambiguous():
    jobs, sources, records = _fixture("needs_review")
    records.pop()
    _add_same_identity_non_class_record(
        sources, records, filename="OCR_Ausiliario.pdf", role="extraction_aid"
    )

    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    pair = result["unidirectional_pairs"][0]
    assert pair["shared_spell_evidence_classification"] == AMBIGUOUS_REVIEW
    assert pair["classification_requires_review"] is True


def test_separate_same_identity_superseded_authority_keeps_pair_ambiguous():
    jobs, sources, records = _fixture("needs_review")
    records.pop()
    _add_same_identity_non_class_record(
        sources,
        records,
        filename="Supplemento_Superseded.pdf",
        role="authority",
        status="superseded",
    )

    result = summarize_verified_authority_shared_spell_evidence(jobs, sources, records)

    pair = result["unidirectional_pairs"][0]
    assert pair["shared_spell_evidence_classification"] == AMBIGUOUS_REVIEW
    assert pair["classification_requires_review"] is True
