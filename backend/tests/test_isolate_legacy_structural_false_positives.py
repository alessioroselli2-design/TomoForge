import asyncio
from copy import deepcopy

from scripts.isolate_legacy_structural_false_positives import (
    ISOLATION_FLAG,
    TARGETS,
    isolate_targets,
    load_targets,
    revalidate_targets,
)


class _Result:
    matched_count = 1


class _Collection:
    def __init__(self, rows):
        self.rows = {row["id"]: deepcopy(row) for row in rows}
        self.queries = []

    async def find_one(self, query):
        row = self.rows.get(query["id"])
        return deepcopy(row) if row else None

    async def update_one(self, query, update):
        self.queries.append(deepcopy(query))
        row = self.rows[query["id"]]
        for key, expected in query.items():
            if row.get(key) != expected:
                result = _Result()
                result.matched_count = 0
                return result
        row.update(deepcopy(update["$set"]))
        return _Result()


def _rows():
    return [
        {
            "id": target["id"],
            "name": target["name"],
            "reference_type": "monster",
            "review_status": "verified",
            "review_flags": [],
            "canonical_id": None,
            "source_text_checksum": f"checksum-{target['id']}",
            "source_refs": [{"filename": "manual.pdf", "page": 1}],
            "attributes": {"classe_armatura": "1", "punti_ferita": "1"},
            "updated_at": "2026-09-19T00:00:00Z",
        }
        for target in TARGETS
    ]


def test_isolation_batch_changes_only_review_metadata_with_one_timestamp():
    rows = _rows()
    collection = _Collection(rows)
    snapshots = asyncio.run(load_targets(collection))
    asyncio.run(revalidate_targets(collection, snapshots))

    timestamp = "2026-09-20T12:34:56Z"
    isolated = asyncio.run(isolate_targets(collection, snapshots, timestamp))

    assert len(isolated) == 3
    assert all(row["review_status"] == "needs_review" for row in isolated)
    assert all(row["review_flags"] == [ISOLATION_FLAG] for row in isolated)
    assert all(row["updated_at"] == timestamp for row in isolated)
    assert all(
        row["attributes"] == before["attributes"]
        for row, before in zip(isolated, rows, strict=True)
    )
    assert all(query["review_status"] == "verified" for query in collection.queries)
    assert all(query["review_flags"] == [] for query in collection.queries)


def test_isolation_preflight_rejects_any_already_reviewed_target():
    rows = _rows()
    rows[1]["review_status"] = "needs_review"
    collection = _Collection(rows)

    try:
        asyncio.run(load_targets(collection))
    except RuntimeError as exc:
        assert "status drift" in str(exc)
    else:
        raise AssertionError("the complete isolation batch must fail before writes")
