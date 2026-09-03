import asyncio

from core.db import MemoryCollection
from services.translation_review import (
    list_owner_reference_records,
    run_translation_reviews,
    translation_review_status,
)
from services.translation_verification import translation_verification_fingerprint


class FakeDB:
    def __init__(self):
        self.private_reference_records = MemoryCollection()


def translated_record(**overrides):
    base = {
        "id": "ref-1",
        "user_id": "owner-1",
        "source_language": "es",
        "source_name": "Saeta de Fuego",
        "source_description": "Inflige 1d10 de daño de fuego.",
        "source_full_text": "Haz un ataque de conjuro a distancia. Inflige 1d10 de daño a 120 pies.",
        "source_attributes": {"damage": "1d10", "range": "120 feet"},
        "name": "Dardo di Fuoco",
        "description": "Infligge 1d10 danni da fuoco.",
        "full_text": "Effettua un attacco a distanza con incantesimo. Infligge 1d10 danni a 120 piedi.",
        "attributes": {"damage": "1d10", "range": "120 piedi"},
        "translation_status": "translated",
        "translation_review_status": "pending",
        "translation_review_fingerprint": "",
        "review_flags": [],
    }
    base.update(overrides)
    return base


def verified_answer(_record):
    return {
        "status": "verified",
        "confidence": 0.99,
        "conflict_fields": [],
        "notes": "Traduzione fedele.",
    }


def test_worker_persists_current_verdict_and_skips_it_on_next_run():
    async def scenario():
        db = FakeDB()
        await db.private_reference_records.insert_one(translated_record())

        first = await run_translation_reviews(
            "owner-1", db=db, batch_size=5, comparator=verified_answer
        )
        stored = await db.private_reference_records.find_one({"id": "ref-1"})
        second = await run_translation_reviews(
            "owner-1", db=db, batch_size=5, comparator=lambda _record: (_ for _ in ()).throw(RuntimeError("must not run"))
        )

        assert first["processed_records"] == 1
        assert first["ai_verified"] == 1
        assert stored["translation_review_status"] == "ai_verified"
        assert stored["translation_review_confidence"] == 0.99
        assert stored["translation_review_fingerprint"] == translation_verification_fingerprint(stored)
        assert second["processed_records"] == 0
        assert second["ai_verified"] == 1
        assert second["ready_for_canonicalization"] is True

    asyncio.run(scenario())


def test_provider_failure_remains_retryable():
    async def scenario():
        db = FakeDB()
        await db.private_reference_records.insert_one(translated_record())

        failed = await run_translation_reviews(
            "owner-1",
            db=db,
            batch_size=1,
            comparator=lambda _record: (_ for _ in ()).throw(RuntimeError("provider down")),
        )
        retried = await run_translation_reviews(
            "owner-1", db=db, batch_size=1, comparator=verified_answer
        )

        assert failed["processed_records"] == 1
        assert failed["failed"] == 1
        assert failed["ready_for_canonicalization"] is False
        assert retried["processed_records"] == 1
        assert retried["ai_verified"] == 1
        assert retried["failed"] == 0

    asyncio.run(scenario())


def test_stale_verdict_returns_to_pending_until_rechecked():
    async def scenario():
        db = FakeDB()
        value = translated_record(translation_review_status="ai_verified")
        value["translation_review_fingerprint"] = translation_verification_fingerprint(value)
        value["full_text"] += " Testo modificato."
        await db.private_reference_records.insert_one(value)

        status = await translation_review_status("owner-1", db=db)

        assert status["stale"] == 1
        assert status["pending"] == 1
        assert status["ready_for_canonicalization"] is False

    asyncio.run(scenario())


def test_untranslated_failures_and_processing_block_canonicalization_readiness():
    async def scenario():
        db = FakeDB()
        await db.private_reference_records.insert_many([
            translated_record(id="failed", translation_status="failed"),
            translated_record(id="processing", translation_status="processing"),
            translated_record(id="pending", translation_status="pending"),
        ])

        status = await translation_review_status("owner-1", db=db)

        assert status["translatable_total"] == 3
        assert status["translated_total"] == 0
        assert status["translation_failed"] == 1
        assert status["translation_processing"] == 1
        assert status["translation_pending"] == 1
        assert status["translation_not_ready"] == 3
        assert status["verification_complete"] == 0
        assert status["ready_for_canonicalization"] is False

    asyncio.run(scenario())


def test_explicit_human_review_remains_a_translation_gate_override():
    async def scenario():
        db = FakeDB()
        await db.private_reference_records.insert_one(translated_record(
            translation_status="failed",
            review_status="verified",
        ))

        status = await translation_review_status("owner-1", db=db)
        result = await run_translation_reviews(
            "owner-1",
            db=db,
            batch_size=5,
            comparator=lambda _record: (_ for _ in ()).throw(RuntimeError("must not run")),
        )

        assert status["human_verified"] == 1
        assert status["translation_failed"] == 0
        assert status["verification_complete"] == 1
        assert status["ready_for_canonicalization"] is True
        assert result["processed_records"] == 0

    asyncio.run(scenario())


def test_owner_record_reader_paginates_the_complete_corpus():
    async def scenario():
        db = FakeDB()
        await db.private_reference_records.insert_many([
            translated_record(id=f"ref-{index}") for index in range(5)
        ])

        records = await list_owner_reference_records("owner-1", db=db, page_size=2)

        assert [record["id"] for record in records] == [
            "ref-0", "ref-1", "ref-2", "ref-3", "ref-4",
        ]

    asyncio.run(scenario())
