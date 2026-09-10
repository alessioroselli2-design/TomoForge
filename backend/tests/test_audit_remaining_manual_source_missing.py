from copy import deepcopy

from scripts.audit_remaining_manual_source_missing import (
    AMBIGUOUS_REVIEW,
    PROVENANCE_MATCH_REVIEW,
    summarize_remaining_manual_source_missing,
)


def _remaining_cases():
    jobs = [
        {
            "id": "job-bardo",
            "filename": "Bardo__1787233073462.pdf",
            "status": "failed",
            "last_error": "manual_source_missing",
            "source_fingerprint": "job-bardo-sha",
            "source_language": "it",
            "page_count": 26,
            "records_imported": 7,
            "records_updated": 100,
        },
        {
            "id": "job-phb-es",
            "filename": "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf",
            "status": "failed",
            "last_error": "manual_source_missing",
            "source_fingerprint": "job-phb-sha",
            "source_language": "es",
            "page_count": 1018,
            "records_updated": 22,
            "records_flagged": 2,
        },
    ]
    sources = [
        {
            "id": "source-bardo",
            "physical_filename": "Bardo .pdf",
            "physical_sha256": "registry-bardo-sha",
            "physical_pages": 26,
            "logical_source_id": "derived_class_bardo",
            "language": "it",
            "source_role": "extraction_aid",
            "source_status": "active",
        },
        {
            "id": "source-phb-es",
            "physical_filename": "731764731-D-D-Manual-Del-Jugador-5e(1).pdf",
            "physical_sha256": "registry-phb-sha",
            "physical_pages": 1018,
            "logical_source_id": "phb_2014_es",
            "language": "es",
            "source_role": "extraction_aid",
            "source_status": "active",
        },
    ]
    return jobs, sources


def test_two_residual_alias_cases_are_ambiguous_and_keep_provenance_and_gate():
    jobs, sources = _remaining_cases()
    original_jobs, original_sources = deepcopy(jobs), deepcopy(sources)

    result = summarize_remaining_manual_source_missing(jobs, sources)

    assert result["manual_source_missing_cases"] == 2
    assert result["classification_counts"] == {AMBIGUOUS_REVIEW: 2}
    assert [case["job_filename"] for case in result["cases"]] == [
        "Bardo__1787233073462.pdf",
        "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf",
    ]
    assert all(case["classification"] == AMBIGUOUS_REVIEW for case in result["cases"])
    assert all(not case["evidence_sufficient_for_provenance_match"] for case in result["cases"])
    assert all(case["requires_manual_review"] for case in result["cases"])
    assert all(len(case["filename_alias_registry_matches"]) == 1 for case in result["cases"])
    assert result["cases"][0]["job_record_activity"]["records_imported"] == 7
    assert result["cases"][0]["job_record_activity"]["records_updated"] == 100
    assert result["cases"][0]["filename_alias_registry_matches"][0]["logical_source_id"] == "derived_class_bardo"
    assert result["cases"][1]["job_record_activity"]["records_updated"] == 22
    assert result["cases"][1]["job_record_activity"]["records_flagged"] == 2
    assert result["cases"][1]["filename_alias_registry_matches"][0]["logical_source_id"] == "phb_2014_es"
    assert all(
        case["filename_alias_registry_matches"][0]["source_role"] == "extraction_aid"
        for case in result["cases"]
    )
    assert jobs == original_jobs
    assert sources == original_sources
    assert result["filename_evidence_is_diagnostic_only"] is True
    assert result["provenance_match_bypasses_review"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_unique_exact_sha_is_reported_but_still_cannot_bypass_review():
    jobs, sources = _remaining_cases()
    jobs = [jobs[0]]
    sources[0]["physical_sha256"] = jobs[0]["source_fingerprint"]

    result = summarize_remaining_manual_source_missing(jobs, sources)

    case = result["cases"][0]
    assert case["classification"] == PROVENANCE_MATCH_REVIEW
    assert case["evidence_sufficient_for_provenance_match"] is True
    assert case["requires_manual_review"] is True
    assert len(case["exact_sha_registry_matches"]) == 1
    assert result["provenance_match_bypasses_review"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_non_target_jobs_and_duplicate_style_errors_are_excluded():
    jobs, sources = _remaining_cases()
    jobs.extend(
        [
            {"status": "completed", "last_error": "manual_source_missing"},
            {
                "status": "failed",
                "last_error": "manual_source_duplicate:other.pdf",
            },
            {"status": "failed", "last_error": "manual_source_missing:detail"},
        ]
    )

    result = summarize_remaining_manual_source_missing(jobs, sources)

    assert result["manual_source_missing_cases"] == 2
