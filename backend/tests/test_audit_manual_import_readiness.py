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
        {
            "status": "failed",
            "filename": "private-b.pdf",
            "last_error": "sensitive failure detail",
            "records_imported": 10,
            "records_flagged": 4,
            "pages_needing_ocr": [2, 3],
            "attempt_count": 2,
            "external_processing_confirmed": True,
            "translation_processing_confirmed": True,
        },
        {"status": "failed", "filename": "private-c.pdf", "last_error": "other detail"},
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
        "failed_jobs_retried": 1,
        "failed_jobs_external_processing_confirmed": 1,
        "failed_jobs_translation_processing_confirmed": 1,
        "structured_import_stable": False,
    }
    rendered = str(result)
    assert "private-a.pdf" not in rendered
    assert "private-b.pdf" not in rendered
    assert "sensitive failure detail" not in rendered


def test_summary_requires_all_jobs_completed_for_stability():
    result = summarize_import_readiness([
        {"status": "completed"},
        {"status": "completed"},
    ])

    assert result["structured_import_stable"] is True
    assert result["jobs_incomplete"] == 0
    assert result["failed_jobs_with_record_activity"] == 0
    assert result["failed_jobs_with_ocr_backlog"] == 0
    assert result["failed_jobs_retried"] == 0


def test_empty_job_history_is_not_treated_as_stable():
    result = summarize_import_readiness([])

    assert result["jobs_total"] == 0
    assert result["job_status_breakdown"] == {}
    assert result["structured_import_stable"] is False
