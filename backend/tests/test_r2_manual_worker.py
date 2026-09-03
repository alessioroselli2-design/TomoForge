import asyncio
from datetime import datetime, timezone

import pytest

from scripts import import_manuals_from_r2 as worker
from scripts.import_manuals_from_r2 import (
    _canonical_filename,
    _local_filename_for_source,
    _parser,
    _pending_sources,
    _resolve_requested_source,
    _safe_pdf_name,
    _stable_mtime,
)


def test_safe_pdf_name_strips_prefix_but_rejects_non_pdf():
    assert _safe_pdf_name("private/manuals/Ranger .pdf") == "Ranger .pdf"
    with pytest.raises(ValueError):
        _safe_pdf_name("private/manuals/readme.txt")


def test_canonical_filename_maps_legacy_replit_alias():
    assert (
        _canonical_filename("Ranger__1787233073462.pdf")
        == "Ranger .pdf"
    )


def test_pending_sources_skip_completed_or_already_imported_sources():
    importable = {
        "A.pdf": {"key": "A.pdf"},
        "B.pdf": {"key": "B.pdf"},
        "C.pdf": {"key": "C.pdf"},
    }
    imported = {"A.pdf", "B.pdf"}
    jobs = {
        "A.pdf": {"filename": "A.pdf", "status": "completed"},
        "B.pdf": {"filename": "B.pdf", "status": "failed"},
    }

    assert _pending_sources(importable, imported, jobs) == ["B.pdf", "C.pdf"]


def test_local_filename_reuses_existing_alias_job():
    jobs = {
        "Ranger .pdf": {
            "filename": "Ranger__1787233073462.pdf",
            "status": "failed",
        }
    }
    assert (
        _local_filename_for_source("Ranger .pdf", jobs)
        == "Ranger__1787233073462.pdf"
    )


def test_requested_source_accepts_legacy_alias():
    importable = {"Ranger .pdf": {"key": "Ranger .pdf"}}
    assert (
        _resolve_requested_source("Ranger__1787233073462.pdf", importable)
        == "Ranger .pdf"
    )


def test_stable_mtime_uses_r2_last_modified_timestamp():
    value = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)
    assert _stable_mtime(value) == value.timestamp()


def test_r2_worker_defaults_to_one_durable_page_chunk():
    args = _parser().parse_args([])

    assert args.max_manuals == 1
    assert args.max_chunks == 1


class _FakeJobs:
    def __init__(self, current):
        self.current = current

    async def find_one(self, _query):
        return dict(self.current)


class _FakeDB:
    def __init__(self, current):
        self.private_manual_import_jobs = _FakeJobs(current)


def test_bounded_worker_rejects_retryable_chunk_without_progress(monkeypatch):
    async def fake_claim(_db, _user_id, _filename):
        return {"status": "processing", "current_page": 13}

    async def fake_process(_user_id, _job, *, db=None):
        return None

    monkeypatch.setattr(worker, "_claim_selected_preload_job", fake_claim)
    import services.preload as preload
    monkeypatch.setattr(preload, "process_manual_preload_job", fake_process)

    db = _FakeDB({
        "status": "queued",
        "current_page": 13,
        "last_error": "temporary_provider_error",
    })

    with pytest.raises(RuntimeError, match="made no progress"):
        asyncio.run(worker._process_selected_chunks(db, "owner", "Large.pdf", 1))


def test_bounded_worker_accepts_advanced_checkpoint(monkeypatch):
    async def fake_claim(_db, _user_id, _filename):
        return {"status": "processing", "current_page": 13}

    async def fake_process(_user_id, _job, *, db=None):
        return None

    monkeypatch.setattr(worker, "_claim_selected_preload_job", fake_claim)
    import services.preload as preload
    monkeypatch.setattr(preload, "process_manual_preload_job", fake_process)

    db = _FakeDB({
        "status": "queued",
        "current_page": 25,
        "last_error": "",
    })

    result = asyncio.run(
        worker._process_selected_chunks(db, "owner", "Large.pdf", 1)
    )
    assert result["current_page"] == 25
