"""Regression tests for the preload endpoint request-validation path.

Ensures that an unknown filename returns HTTP 400 (not 502 from UnboundLocalError)
and that no import job is created or worker started for that request.
"""

import asyncio
from pathlib import Path

import pytest
import server
import services.library as lib_mod
import services.preload as preload_mod


class MemoryJobs:
    def __init__(self, docs=None):
        self.documents = list(docs or [])

    def find(self, _query=None):
        return self

    def sort(self, *_a, **_kw):
        return self

    async def to_list(self, _limit):
        return list(self.documents)

    async def insert_one(self, doc):
        self.documents.append(doc)

    async def update_one(self, _q, _u, upsert=False):
        pass

    async def find_one(self, query):
        for doc in self.documents:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None


class FakeDB:
    def __init__(self):
        self.private_manual_import_jobs = MemoryJobs()
        self.private_reference_records = MemoryJobs()


def test_preload_unknown_filename_returns_400(monkeypatch):
    """POST /api/library/preload with an unknown filename must be rejected with 400.

    Before the fix, ensure_manual_preload_jobs raised UnboundLocalError because
    HTTPException was imported after its first use, turning this into a 502.
    """
    fake_db = FakeDB()
    started = []

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {"Reale.pdf": Path("/fake/Reale.pdf")})
    monkeypatch.setattr(preload_mod, "start_manual_preload_worker", lambda user_id: started.append(user_id))

    body = server.ManualPreloadInput(filename="NonEsistente.pdf")

    with pytest.raises(Exception) as exc_info:
        asyncio.run(server.ensure_manual_preload_jobs("owner-1", body))

    from fastapi import HTTPException
    assert isinstance(exc_info.value, HTTPException), (
        f"Expected HTTPException, got {type(exc_info.value).__name__}: {exc_info.value}"
    )
    assert exc_info.value.status_code == 400
    assert started == [], "No worker must be started for an unknown filename"
    assert fake_db.private_manual_import_jobs.documents == [], (
        "No import job must be created for an unknown filename"
    )


def test_preload_valid_filename_does_not_raise(monkeypatch):
    """POST /api/library/preload with a known filename must not raise."""
    fake_db = FakeDB()
    started = []
    fake_path = Path("/fake/Reale.pdf")

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {"Reale.pdf": fake_path})
    monkeypatch.setattr(preload_mod, "start_manual_preload_worker", lambda user_id: started.append(user_id))
    monkeypatch.setattr(lib_mod, "manual_requires_ocr", lambda filename: False)
    monkeypatch.setattr(lib_mod, "manual_source_fingerprint", lambda _p: "fp-stable")
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _p: 20)
    monkeypatch.setattr(lib_mod, "manual_source_language", lambda filename: "it")

    body = server.ManualPreloadInput(filename="Reale.pdf")

    # Should complete without raising — a job is created in the queue
    asyncio.run(server.ensure_manual_preload_jobs("owner-1", body, db=fake_db))
    assert len(fake_db.private_manual_import_jobs.documents) >= 1
