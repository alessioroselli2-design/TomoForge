"""Worker-level coverage for page-local OCR failures and durable checkpoints."""
import asyncio
import copy
from types import SimpleNamespace

import server
import services.library as library
import services.preload as preload

USER_ID = "ocr-worker-owner"
FILENAME = "mixed-manual.pdf"


def _job(page=1, lease="lease-1", unresolved=None):
    return {"id": "ocr-job", "user_id": USER_ID, "filename": FILENAME,
            "status": "processing", "current_page": page, "attempt_count": 0,
            "last_error": "", "pages_needing_ocr": list(unresolved or []),
            "records_imported": 0, "records_updated": 0, "records_flagged": 0,
            "records_skipped": 0, "lease_id": lease, "lease_expires_at": 9999999999}


def _setup(monkeypatch, tmp_path, job, page_count, batch_size, importer):
    source = tmp_path / FILENAME
    source.write_bytes(b"synthetic PDF placeholder")
    jobs = server.MemoryCollection()
    jobs.rows.append(copy.deepcopy(job))
    db = SimpleNamespace(private_manual_import_jobs=jobs)
    monkeypatch.setattr(library, "available_reference_manuals", lambda: {FILENAME: source})
    monkeypatch.setattr(library, "manual_page_count", lambda _path: page_count)
    monkeypatch.setattr(library, "manual_source_duplicate_of", lambda *_args: None)
    monkeypatch.setattr(library, "manual_requires_ocr", lambda _filename: True)
    monkeypatch.setattr(library, "import_private_reference_manuals", importer)
    monkeypatch.setattr(preload, "MANUAL_PRELOAD_PAGE_BATCH_SIZE", batch_size)
    return db, jobs


def _report(imported=0, unresolved=None):
    return server.ReferenceImportResult(imported=imported, updated=0,
        flagged_for_review=imported, skipped=0,
        sources=[{"filename": FILENAME, "pages_needing_ocr": list(unresolved or [])}])


def test_mixed_native_and_successful_ocr_pages_complete_worker_chunk(monkeypatch, tmp_path):
    async def importer(*_args, **_kwargs):
        return _report(imported=2)
    job = _job()
    db, jobs = _setup(monkeypatch, tmp_path, job, 2, 2, importer)
    asyncio.run(preload.process_manual_preload_job(USER_ID, job, db=db))
    stored = jobs.rows[0]
    assert (stored["status"], stored["current_page"]) == ("completed", 3)
    assert (stored["records_imported"], stored["records_flagged"]) == (2, 2)
    assert stored["pages_needing_ocr"] == []


def test_failed_or_blank_ocr_page_is_preserved_while_worker_advances(monkeypatch, tmp_path):
    async def importer(*_args, **_kwargs):
        return _report(imported=1, unresolved=[2])
    job = _job()
    db, jobs = _setup(monkeypatch, tmp_path, job, 2, 2, importer)
    asyncio.run(preload.process_manual_preload_job(USER_ID, job, db=db))
    stored = jobs.rows[0]
    assert (stored["status"], stored["current_page"]) == ("completed", 3)
    assert stored["pages_needing_ocr"] == [2]
    assert stored["last_error"] == "ocr_pages_unresolved"
    assert stored["attempt_count"] == 0
    assert stored["records_imported"] == 1


def test_unresolved_page_in_first_chunk_does_not_block_later_chunks(monkeypatch, tmp_path):
    calls = []
    async def importer(_user_id, body, **_kwargs):
        calls.append((body.start_page, body.end_page))
        return _report(imported=1, unresolved=[1] if body.start_page == 1 else [])
    job = _job()
    db, jobs = _setup(monkeypatch, tmp_path, job, 4, 2, importer)
    asyncio.run(preload.process_manual_preload_job(USER_ID, job, db=db))
    assert jobs.rows[0]["current_page"] == 3
    assert jobs.rows[0]["pages_needing_ocr"] == [1]
    jobs.rows[0].update(status="processing", lease_id="lease-2")
    asyncio.run(preload.process_manual_preload_job(USER_ID, copy.deepcopy(jobs.rows[0]), db=db))
    assert calls == [(1, 2), (3, 4)]
    assert (jobs.rows[0]["status"], jobs.rows[0]["current_page"]) == ("completed", 5)
    assert jobs.rows[0]["pages_needing_ocr"] == [1]
    assert jobs.rows[0]["records_imported"] == 2


def test_real_import_error_keeps_existing_retry_then_failure_semantics(monkeypatch, tmp_path):
    async def importer(*_args, **_kwargs):
        raise RuntimeError("database unavailable")
    job = _job()
    db, jobs = _setup(monkeypatch, tmp_path, job, 2, 2, importer)
    monkeypatch.setattr(preload, "MANUAL_PRELOAD_MAX_ATTEMPTS", 2)
    asyncio.run(preload.process_manual_preload_job(USER_ID, job, db=db))
    assert (jobs.rows[0]["status"], jobs.rows[0]["current_page"], jobs.rows[0]["attempt_count"]) == ("queued", 1, 1)
    jobs.rows[0].update(status="processing", lease_id="lease-2")
    asyncio.run(preload.process_manual_preload_job(USER_ID, copy.deepcopy(jobs.rows[0]), db=db))
    assert (jobs.rows[0]["status"], jobs.rows[0]["current_page"], jobs.rows[0]["attempt_count"]) == ("failed", 1, 2)
    assert jobs.rows[0]["last_error"] == "database unavailable"
