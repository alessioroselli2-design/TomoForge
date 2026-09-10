from scripts.audit_bounded_ocr_pilot_candidates import (
    NOT_ELIGIBLE,
    PROVENANCE_REVIEW,
    READY,
    STRUCTURED,
    summarize_bounded_ocr_pilot_candidates,
)


def _source(**overrides):
    source = {
        "id": "src-ready",
        "physical_filename": "Small Authority.pdf",
        "physical_sha256": "sha-ready",
        "physical_pages": 22,
        "logical_source_id": "small_2019_en",
        "language": "en",
        "ruleset": "2014",
        "source_role": "authority",
        "source_status": "active",
        "import_state": "catalogued",
        "text_mode": "vision_required",
        "imported_record_count": 0,
    }
    source.update(overrides)
    return source


def test_unique_active_authority_is_ranked_ready_without_authorizing_ocr():
    result = summarize_bounded_ocr_pilot_candidates([_source()], [])

    assert result["classification_counts"][READY] == 1
    assert result["recommended_pilot_source_id"] == "src-ready"
    assert result["ready_candidates_ranked"][0]["classification"] == READY
    assert result["ocr_authorized"] is False
    assert result["external_paid_api_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_same_sha_across_different_logical_sources_requires_provenance_review():
    sources = [
        _source(),
        _source(id="src-other", logical_source_id="different_2020_en"),
    ]
    result = summarize_bounded_ocr_pilot_candidates(sources, [])

    assert result["classification_counts"][PROVENANCE_REVIEW] == 2
    assert result["recommended_pilot_source_id"] is None
    assert all(row["same_sha_logical_source_count"] == 2 for row in result["all_sources"])


def test_existing_registry_or_job_activity_is_not_a_fresh_pilot_candidate():
    source_with_records = _source(id="src-records", physical_sha256="sha-records", imported_record_count=3)
    source_with_job = _source(id="src-job", physical_sha256="sha-job", physical_filename="Job Source.pdf")
    jobs = [{
        "source_fingerprint": "sha-job",
        "status": "completed",
        "records_imported": 2,
        "records_updated": 1,
        "records_flagged": 0,
        "records_skipped": 0,
    }]

    result = summarize_bounded_ocr_pilot_candidates([source_with_records, source_with_job], jobs)

    assert result["classification_counts"][STRUCTURED] == 2
    assert result["recommended_pilot_source_id"] is None


def test_extraction_aid_and_prior_failed_job_stay_behind_review_gate():
    extraction = _source(id="src-aid", physical_sha256="sha-aid", source_role="extraction_aid")
    failed = _source(id="src-failed", physical_sha256="sha-failed", physical_filename="Failed.pdf")
    jobs = [{
        "source_fingerprint": "sha-failed",
        "status": "failed",
        "records_imported": 0,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
    }]

    result = summarize_bounded_ocr_pilot_candidates([extraction, failed], jobs)

    assert result["classification_counts"][PROVENANCE_REVIEW] == 2
    assert all(row["requires_manual_review"] for row in result["all_sources"])


def test_non_active_or_non_vision_sources_are_not_eligible():
    sources = [
        _source(id="inactive", physical_sha256="sha-inactive", source_status="superseded"),
        _source(id="native", physical_sha256="sha-native", text_mode="native_text"),
    ]
    result = summarize_bounded_ocr_pilot_candidates(sources, [])

    assert result["classification_counts"][NOT_ELIGIBLE] == 2
    assert result["recommended_pilot_source_id"] is None
