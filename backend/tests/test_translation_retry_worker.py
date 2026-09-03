import asyncio

from core.db import MemoryCollection
import services.translation_retry as retry_mod
from services.translation_retry import (
    list_owner_reference_records,
    run_translation_retries,
    translation_retry_status,
)


class FakeDB:
    def __init__(self):
        self.private_reference_records = MemoryCollection()


def failed_record(**overrides):
    base = {
        "id": "ref-1",
        "user_id": "owner-1",
        "source_language": "es",
        "source_name": "Bárbaro",
        "source_description": "Un guerrero feroz.",
        "source_full_text": "Un guerrero feroz que combate con furia.",
        "source_attributes": {"dado_vita": "d12"},
        "name": "Bárbaro",
        "description": "Un guerriero feroce.",
        "full_text": "Un guerriero feroce che combatte con furia.",
        "attributes": {"dado_vita": "d12"},
        "translation_status": "failed",
        "translation_error": "provider_translation_incomplete",
        "review_status": "needs_review",
        "review_flags": ["traduzione_da_verificare"],
    }
    base.update(overrides)
    return base


def test_retry_status_counts_retryable_and_blocked_failures():
    async def scenario():
        db = FakeDB()
        await db.private_reference_records.insert_many([
            failed_record(id="retryable"),
            failed_record(id="blocked", translation_error="manual_intervention_required"),
            failed_record(id="human", review_status="verified"),
        ])

        status = await translation_retry_status("owner-1", db=db)

        assert status["failed_total"] == 2
        assert status["retryable_total"] == 1
        assert status["blocked_total"] == 1
        assert status["errors"] == {
            "manual_intervention_required": 1,
            "provider_translation_incomplete": 1,
        }
        assert status["ready_for_verification"] is False

    asyncio.run(scenario())


def test_retry_worker_is_bounded_and_reuses_single_record_retry(monkeypatch):
    async def scenario():
        db = FakeDB()
        await db.private_reference_records.insert_many([
            failed_record(id="ref-1"),
            failed_record(id="ref-2"),
            failed_record(id="ref-3"),
        ])
        retried = []

        async def fake_retry(user_id, reference_id, *, db):
            retried.append(reference_id)
            await db.private_reference_records.update_one(
                {"id": reference_id, "user_id": user_id},
                {"$set": {"translation_status": "translated", "translation_error": ""}},
            )
            return await db.private_reference_records.find_one({
                "id": reference_id,
                "user_id": user_id,
            })

        monkeypatch.setattr(retry_mod, "retry_private_reference_translation", fake_retry)

        result = await run_translation_retries("owner-1", db=db, batch_size=2)

        assert retried == ["ref-1", "ref-2"]
        assert result["processed_records"] == 2
        assert result["recovered_records"] == 2
        assert result["still_failed_records"] == 0
        assert result["failed_total"] == 1
        assert result["retryable_total"] == 1

    asyncio.run(scenario())


def test_retry_worker_reports_persistent_failure(monkeypatch):
    async def scenario():
        db = FakeDB()
        await db.private_reference_records.insert_one(failed_record())

        async def fake_retry(user_id, reference_id, *, db):
            return await db.private_reference_records.find_one({
                "id": reference_id,
                "user_id": user_id,
            })

        monkeypatch.setattr(retry_mod, "retry_private_reference_translation", fake_retry)

        result = await run_translation_retries("owner-1", db=db, batch_size=5)

        assert result["processed_records"] == 1
        assert result["recovered_records"] == 0
        assert result["still_failed_records"] == 1
        assert result["retryable_total"] == 1
        assert result["ready_for_verification"] is False

    asyncio.run(scenario())


def test_owner_record_reader_paginates_complete_retry_corpus():
    async def scenario():
        db = FakeDB()
        await db.private_reference_records.insert_many([
            failed_record(id=f"ref-{index}") for index in range(5)
        ])

        records = await list_owner_reference_records("owner-1", db=db, page_size=2)

        assert [record["id"] for record in records] == [
            "ref-0", "ref-1", "ref-2", "ref-3", "ref-4",
        ]

    asyncio.run(scenario())
