import asyncio
from datetime import datetime, timezone

from scripts.repair_monsters_from_source import (
    OCR_REVIEW_FLAG,
    REPAIR_FLAG,
    _apply_update,
)


class _Result:
    matched_count = 1


class _Collection:
    def __init__(self):
        self.query = None
        self.update = None
        self.row = None

    async def update_one(self, query, update):
        self.query = query
        self.update = update
        self.row = dict(update["$set"])
        return _Result()

    async def find_one(self, query):
        return self.row


def test_apply_update_sets_fresh_utc_updated_at_and_preserves_guards():
    collection = _Collection()
    legacy = {
        "id": "monster-1",
        "canonical_id": None,
        "review_status": "verified",
        "source_text_checksum": "abc123",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    proposal = {
        "attributes": {
            "classe_armatura": "18 (armatura naturale)",
            "punti_ferita": "304 (32d10 + 128)",
            "velocita": "9 m",
        },
        "review_flags": [OCR_REVIEW_FLAG, REPAIR_FLAG],
        "review_status": "pending",
    }

    before = datetime.now(timezone.utc)
    asyncio.run(_apply_update(collection, legacy, proposal))
    after = datetime.now(timezone.utc)

    assert collection.query == {
        "id": "monster-1",
        "review_status": "verified",
        "source_text_checksum": "abc123",
    }
    payload = collection.update["$set"]
    assert payload["attributes"] == proposal["attributes"]
    assert payload["review_status"] == "pending"
    assert payload["review_flags"] == [OCR_REVIEW_FLAG, REPAIR_FLAG]
    assert isinstance(payload["updated_at"], datetime)
    assert payload["updated_at"].tzinfo == timezone.utc
    assert before <= payload["updated_at"] <= after
