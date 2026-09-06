import asyncio

from scripts.audit_manual_import_readiness import fetch_all, summarize_import_readiness


class FakeCollection:
    def __init__(self, rows):
        self.rows = rows
        self.offsets = []

    def find(self, query):
        assert query == {}
        return self

    async def to_list(self, limit, offset=0):
        self.offsets.append(offset)
        return self.rows[offset:offset + limit]


def test_fetch_all_reads_every_job_once():
    collection = FakeCollection([{"id": index} for index in range(5)])
    result = asyncio.run(fetch_all(collection, page_size=2))
    assert [row["id"] for row in result] == list(range(5))
    assert collection.offsets == [0, 2, 4]


def test_summary_marks_failed_imports_as_not_stable_and_reports_partial_activity():
    jobs = [
        {"status": "completed", "filename": "private-a.pdf", "last_error": None},
        {"status": "failed", "filename": "private-b.pdf", "last_error": "PGRST204: Could not find column in the schema cache", "records_imported": 10, "records_flagged": 4, "pages_needing_ocr": [2, 3], "attempt_count": 2, "external_processing_confirmed": True, "translation_processing_confirmed": True},
        {"status": "failed", "filename": "private-c.pdf", "last_error": "PGRST204: Could not find the level column in the schema cache", "attempt_count": 3},
    ]
    result = summarize_import_readiness(jobs)
    assert result == {
        "jobs_total": 3,
        "job_status_breakdown": {"completed": 1, "failed": 2},
        "jobs_completed": 1,
        "jobs_failed": 2,
        "jobs_incomplete": 2,
        "failed_jobs_with_record_activity": 1,
        "failed_jobs_with_ocr_backlog": 1,
        "failed_jobs_without_ocr_backlog": 1,
        "failed_jobs_schema_cache_miss": 2,
        "failed_jobs_schema_cache_miss_without_ocr_backlog": 1,
        "failed_jobs_non_schema_cache_without_ocr_backlog": 0,
        "failed_jobs_manual_source_duplicate": 0,
        "failed_jobs_manual_source_duplicate_reconciliation_candidates": 0,
        "failed_jobs_manual_source_duplicate_reconciled": 0,
        "failed_jobs_manual_source_duplicate_ambiguous": 0,
        "failed_jobs_manual_source_duplicate_unmatched": 0,
        "failed_jobs_duplicate_like": 0,
        "failed_jobs_duplicate_like_investigation_candidates": 0,
        "failed_jobs_schema_cache_retry_candidates": 0,
        "failed_jobs_non_schema_investigation_candidates": 0,
        "failed_jobs_retried": 2,
        "failed_jobs_retried_without_ocr_backlog": 1,
        "failed_jobs_external_processing_confirmed": 1,
        "failed_jobs_translation_processing_confirmed": 1,
        "structured_import_stable": False,
    }
    rendered = str(result)
    assert "private-a.pdf" not in rendered
    assert "private-b.pdf" not in rendered
    assert "PGRST204" not in rendered
    assert "level column" not in rendered


def test_summary_requires_all_jobs_completed_for_stability():
    result = summarize_import_readiness([{"status": "completed"}, {"status": "completed"}])
    assert result["structured_import_stable"] is True
    assert result["jobs_incomplete"] == 0
    assert result["failed_jobs_with_record_activity"] == 0
    assert result["failed_jobs_with_ocr_backlog"] == 0
    assert result["failed_jobs_without_ocr_backlog"] == 0
    assert result["failed_jobs_schema_cache_miss"] == 0
    assert result["failed_jobs_schema_cache_miss_without_ocr_backlog"] == 0
    assert result["failed_jobs_non_schema_cache_without_ocr_backlog"] == 0
    assert result["failed_jobs_manual_source_duplicate"] == 0
    assert result["failed_jobs_manual_source_duplicate_reconciliation_candidates"] == 0
    assert result["failed_jobs_manual_source_duplicate_reconciled"] == 0
    assert result["failed_jobs_manual_source_duplicate_ambiguous"] == 0
    assert result["failed_jobs_manual_source_duplicate_unmatched"] == 0
    assert result["failed_jobs_duplicate_like"] == 0
    assert result["failed_jobs_duplicate_like_investigation_candidates"] == 0
    assert result["failed_jobs_schema_cache_retry_candidates"] == 0
    assert result["failed_jobs_non_schema_investigation_candidates"] == 0
    assert result["failed_jobs_retried"] == 0
    assert result["failed_jobs_retried_without_ocr_backlog"] == 0


def test_schema_cache_retry_candidate_requires_no_ocr_no_activity_and_no_prior_retry():
    jobs = [
        {"status": "failed", "last_error": "PGRST204: schema cache miss", "pages_needing_ocr": []},
        {"status": "failed", "last_error": "PGRST204: schema cache miss", "pages_needing_ocr": [1]},
        {"status": "failed", "last_error": "PGRST204: schema cache miss", "records_updated": 1, "pages_needing_ocr": []},
        {"status": "failed", "last_error": "PGRST204: schema cache miss", "attempt_count": 2, "pages_needing_ocr": []},
    ]
    result = summarize_import_readiness(jobs)
    assert result["failed_jobs_schema_cache_miss"] == 4
    assert result["failed_jobs_schema_cache_retry_candidates"] == 1
    assert result["failed_jobs_retried"] == 1


def test_non_schema_cache_failure_is_counted_coarsely_without_exposing_error():
    result = summarize_import_readiness([{"status": "failed", "last_error": "PGRST116: no rows returned", "pages_needing_ocr": []}])
    assert result["failed_jobs_schema_cache_miss"] == 0
    assert result["failed_jobs_schema_cache_miss_without_ocr_backlog"] == 0
    assert result["failed_jobs_non_schema_cache_without_ocr_backlog"] == 1
    assert result["failed_jobs_manual_source_duplicate"] == 0
    assert result["failed_jobs_duplicate_like"] == 0
    assert result["failed_jobs_schema_cache_retry_candidates"] == 0
    assert result["failed_jobs_non_schema_investigation_candidates"] == 1
    assert "PGRST116" not in str(result)
    assert "no rows returned" not in str(result)


def test_duplicate_like_failure_is_counted_without_authorizing_retry():
    result = summarize_import_readiness([{"status": "failed", "last_error": "duplicate source fingerprint", "pages_needing_ocr": []}])
    assert result["failed_jobs_manual_source_duplicate"] == 0
    assert result["failed_jobs_duplicate_like"] == 1
    assert result["failed_jobs_duplicate_like_investigation_candidates"] == 1
    assert result["failed_jobs_schema_cache_retry_candidates"] == 0
    assert result["failed_jobs_non_schema_investigation_candidates"] == 1
    assert "duplicate source fingerprint" not in str(result)


def test_manual_source_duplicate_is_classified_for_reconciliation_without_leaking_payload():
    private_payload = "manual_source_duplicate:private-manual-name.pdf"
    result = summarize_import_readiness([
        {"status": "failed", "last_error": private_payload, "pages_needing_ocr": []},
    ])
    assert result["failed_jobs_manual_source_duplicate"] == 1
    assert result["failed_jobs_manual_source_duplicate_reconciliation_candidates"] == 1
    assert result["failed_jobs_manual_source_duplicate_unmatched"] == 1
    assert result["failed_jobs_duplicate_like"] == 1
    assert result["failed_jobs_schema_cache_retry_candidates"] == 0
    assert result["structured_import_stable"] is False
    assert private_payload not in str(result)
    assert "private-manual-name.pdf" not in str(result)


def test_manual_source_duplicate_reconciles_upload_suffix_to_single_logical_source():
    private_payload = "manual_source_duplicate:Rules_Book__1787259882002.pdf"
    jobs = [{"status": "failed", "last_error": private_payload, "pages_needing_ocr": []}]
    sources = [
        {"physical_filename": "Rules Book.pdf", "logical_source_id": "rules_2014", "source_status": "active"},
        {"physical_filename": "Rules Book (1).pdf", "logical_source_id": "rules_2014", "source_status": "duplicate"},
    ]
    result = summarize_import_readiness(jobs, sources)
    assert result["failed_jobs_manual_source_duplicate_reconciled"] == 1
    assert result["failed_jobs_manual_source_duplicate_ambiguous"] == 0
    assert result["failed_jobs_manual_source_duplicate_unmatched"] == 0
    assert result["structured_import_stable"] is False
    assert private_payload not in str(result)
    assert "Rules Book.pdf" not in str(result)


def test_manual_source_duplicate_remains_ambiguous_across_logical_sources():
    jobs = [{"status": "failed", "last_error": "manual_source_duplicate:Rules_Book__1787259882002.pdf", "pages_needing_ocr": []}]
    sources = [
        {"physical_filename": "Rules Book.pdf", "logical_source_id": "rules_a", "source_status": "active"},
        {"physical_filename": "Rules Book (1).pdf", "logical_source_id": "rules_b", "source_status": "duplicate"},
    ]
    result = summarize_import_readiness(jobs, sources)
    assert result["failed_jobs_manual_source_duplicate_reconciled"] == 0
    assert result["failed_jobs_manual_source_duplicate_ambiguous"] == 1


def test_manual_source_duplicate_with_activity_is_not_reconciliation_candidate():
    result = summarize_import_readiness([
        {"status": "failed", "last_error": "manual_source_duplicate:hidden.pdf", "records_imported": 1, "pages_needing_ocr": []},
    ])
    assert result["failed_jobs_manual_source_duplicate"] == 1
    assert result["failed_jobs_manual_source_duplicate_reconciliation_candidates"] == 0
    assert result["failed_jobs_manual_source_duplicate_reconciled"] == 0


def test_non_schema_cache_failure_with_ocr_backlog_is_not_in_non_ocr_signal():
    result = summarize_import_readiness([{"status": "failed", "last_error": "timeout", "pages_needing_ocr": [4]}])
    assert result["failed_jobs_non_schema_cache_without_ocr_backlog"] == 0
    assert result["failed_jobs_non_schema_investigation_candidates"] == 0


def test_non_schema_investigation_candidate_excludes_partial_activity_and_retries():
    result = summarize_import_readiness([
        {"status": "failed", "last_error": "unknown failure", "records_imported": 1, "pages_needing_ocr": []},
        {"status": "failed", "last_error": "unknown failure", "attempt_count": 2, "pages_needing_ocr": []},
        {"status": "failed", "last_error": "unknown failure", "pages_needing_ocr": []},
    ])
    assert result["failed_jobs_non_schema_cache_without_ocr_backlog"] == 3
    assert result["failed_jobs_non_schema_investigation_candidates"] == 1


def test_empty_job_history_is_not_treated_as_stable():
    result = summarize_import_readiness([])
    assert result["jobs_total"] == 0
    assert result["job_status_breakdown"] == {}
    assert result["structured_import_stable"] is False
