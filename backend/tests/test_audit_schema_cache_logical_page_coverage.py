from scripts.audit_schema_cache_logical_page_coverage import (
    summarize_schema_cache_logical_page_coverage,
)


def _job(**overrides):
    job = {
        "status": "failed",
        "last_error": "PGRST204 schema cache",
        "records_imported": 2,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "current_page": 3,
        "page_count": 6,
        "filename": "Manuale_1700000000000.pdf",
    }
    job.update(overrides)
    return job


def _source(filename, logical_id="manuale", status="active"):
    return {
        "physical_filename": filename,
        "logical_source_id": logical_id,
        "source_status": status,
    }


def _record(filename, page):
    return {
        "id": f"{filename}-{page}",
        "source_refs": [{"filename": filename, "page": page}],
    }


def test_alternate_logical_source_can_close_some_direct_page_gaps():
    result = summarize_schema_cache_logical_page_coverage(
        [_job()],
        [
            _source("Manuale_1700000000000.pdf"),
            _source("Manuale-seconda-copia.pdf"),
        ],
        [
            _record("Manuale.pdf", 1),
            _record("Manuale.pdf", 3),
            _record("Manuale.pdf", 6),
            _record("Manuale-seconda-copia.pdf", 2),
            _record("Manuale-seconda-copia.pdf", 4),
        ],
    )

    assert result["with_reconciled_logical_identity"] == 1
    assert result["direct_missing_pages_total"] == 3
    assert result["logical_identity_missing_pages_total"] == 1
    assert result["direct_gaps_closed_by_alternate_provenance"] == 2
    assert result["jobs_with_any_gap_closed_by_alternate_provenance"] == 1
    assert result["jobs_with_all_direct_gaps_closed_by_alternate_provenance"] == 0


def test_full_logical_page_coverage_never_confirms_record_set_completeness():
    result = summarize_schema_cache_logical_page_coverage(
        [_job()],
        [
            _source("Manuale_1700000000000.pdf"),
            _source("Manuale-seconda-copia.pdf"),
        ],
        [
            _record("Manuale.pdf", 1),
            _record("Manuale.pdf", 3),
            _record("Manuale.pdf", 6),
            _record("Manuale-seconda-copia.pdf", 2),
            _record("Manuale-seconda-copia.pdf", 4),
            _record("Manuale-seconda-copia.pdf", 5),
        ],
    )

    assert result["logical_identity_missing_pages_total"] == 0
    assert result["jobs_with_all_direct_gaps_closed_by_alternate_provenance"] == 1
    assert result["record_set_completeness_confirmed"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_ambiguous_identity_is_not_used_for_logical_page_coverage():
    result = summarize_schema_cache_logical_page_coverage(
        [_job()],
        [
            _source("Manuale_1700000000000.pdf", logical_id="a"),
            _source("Manuale_1700000000000.pdf", logical_id="b"),
        ],
        [_record("Manuale.pdf", 1)],
    )

    assert result["with_reconciled_logical_identity"] == 0
    assert result["with_ambiguous_logical_identity"] == 1
    assert result["direct_gaps_closed_by_alternate_provenance"] == 0
