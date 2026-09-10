from scripts.audit_failed_import_alias_reciprocal_provenance import summarize_reciprocal_provenance


def _job(filename: str) -> dict:
    return {
        "id": "job-1",
        "filename": filename,
        "source_fingerprint": "job-sha",
        "status": "failed",
        "last_error": "manual_source_missing",
    }


def _source(filename: str) -> dict:
    return {
        "id": "src-1",
        "physical_filename": filename,
        "physical_sha256": "registry-sha",
        "logical_source_id": "derived_class_bardo",
    }


def test_reciprocal_and_nonreciprocal_companions_are_distinguished():
    failed = "Bardo__1787233073462.pdf"
    reciprocal = "Mago__1787233073462.pdf"
    one_way = "Stregone__1787233073462.pdf"
    records = [
        {"source_key": failed, "source_refs": [{"filename": failed}, {"filename": reciprocal}, {"filename": one_way}]},
        {"source_key": failed, "source_refs": [{"filename": failed}, {"filename": reciprocal}]},
        {"source_key": reciprocal, "source_refs": [{"filename": reciprocal}, {"filename": failed}]},
        {"source_key": reciprocal, "source_refs": [{"filename": reciprocal}]},
        {"source_key": one_way, "source_refs": [{"filename": one_way}]},
    ]

    result = summarize_reciprocal_provenance([_job(failed)], [_source("Bardo .pdf")], records)

    assert result["review_only_alias_candidates"] == 1
    candidate = result["candidates"][0]
    assert candidate["logical_source_id"] == "derived_class_bardo"
    assert candidate["all_companions_reciprocal"] is False
    assert candidate["companions"] == [
        {
            "filename": reciprocal,
            "forward_mixed_records": 2,
            "companion_source_records": 2,
            "reciprocal_records": 1,
            "has_reciprocal_provenance": True,
        },
        {
            "filename": one_way,
            "forward_mixed_records": 1,
            "companion_source_records": 1,
            "reciprocal_records": 0,
            "has_reciprocal_provenance": False,
        },
    ]
    assert candidate["hash_confirmed"] is False
    assert candidate["requires_manual_reconciliation"] is True
    assert result["reciprocity_confirms_identity"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["translation_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_exact_hash_match_is_not_a_review_candidate():
    filename = "Book_1787286581630.pdf"
    job = {**_job(filename), "source_fingerprint": "same-sha"}
    source = {**_source("Book.pdf"), "physical_sha256": "same-sha"}
    result = summarize_reciprocal_provenance([job], [source], [])
    assert result["review_only_alias_candidates"] == 0
    assert result["candidates"] == []
