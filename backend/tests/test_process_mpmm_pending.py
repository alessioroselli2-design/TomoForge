from __future__ import annotations

import asyncio

import pytest

from scripts import process_mpmm_pending as process


def _record(identifier: str, name: str, *, flags=None) -> dict:
    return {
        "id": identifier,
        "user_id": "owner-1",
        "name": name,
        "reference_type": "monster",
        "review_status": "pending",
        "review_flags": flags or ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": f"checksum-{identifier}",
        "source_refs": [{"logical_source_id": "mpmm_2022_it", "page": 12}],
        "attributes": {
            "classe_armatura": "15",
            "punti_ferita": "45 (6d10 + 12)",
            "velocita": "9 m",
        },
        "canonical_id": None,
    }


def test_mpmm_selection_requires_monster_and_explicit_logical_provenance():
    record = _record("one", "Uno")
    assert process._is_mpmm(record)
    assert not process._is_mpmm({**record, "reference_type": "race"})
    assert not process._is_mpmm({**record, "source_refs": [{"page": 12}]})


def test_partition_is_deterministic_and_never_exceeds_25():
    records = [_record(str(index), f"Mostro {index:03}") for index in range(61, -1, -1)]
    batches = process._partition(records, 25)
    assert [len(batch) for batch in batches] == [25, 25, 12]
    assert [row["name"] for batch in batches for row in batch] == sorted(
        row["name"] for row in records
    )


def test_verified_proposal_removes_only_the_two_authorized_review_flags():
    record = _record("one", "Uno")
    proposal = process._verified_proposal({"after": record})
    assert proposal == {
        "attributes": record["attributes"],
        "review_flags": [],
        "review_status": "verified",
    }


def test_verified_proposal_fails_closed_on_residual_review_flag():
    record = _record("one", "Uno", flags=["ocr_da_verificare", "table_isolation"])
    with pytest.raises(process.repair.RepairBlocked) as exc:
        process._verified_proposal({"after": record})
    assert exc.value.reason == "residual_review_flags"


class _Result:
    matched_count = 1


class _Collection:
    def __init__(self, row):
        self.row = dict(row)

    async def update_one(self, query, update):
        assert query["review_status"] == "pending"
        self.row.update(update["$set"])
        return _Result()

    async def find_one(self, query):
        return dict(self.row) if query["id"] == self.row["id"] else None


class _History:
    def __init__(self):
        self.rows = []

    async def insert_one(self, row):
        self.rows.append(dict(row))

    async def delete_one(self, query):
        self.rows = [row for row in self.rows if row["id"] != query["id"]]
        return _Result()


def test_apply_verified_preserves_provenance_and_records_review_history():
    original = _record("one", "Uno")
    collection = _Collection(original)
    history = _History()
    timestamp = "2026-10-01T08:57:00Z"
    proposal = process._verified_proposal({"after": original})

    asyncio.run(
        process._apply_verified(
            collection, history, original, proposal, updated_at=timestamp
        )
    )

    assert collection.row["review_status"] == "verified"
    assert collection.row["review_flags"] == []
    assert collection.row["source_refs"] == original["source_refs"]
    assert collection.row["canonical_id"] is None
    assert collection.row["updated_at"] == timestamp
    assert len(history.rows) == 1
    assert history.rows[0]["reference_id"] == "one"
    assert history.rows[0]["review_status"] == "verified"
