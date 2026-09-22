import asyncio

from scripts.verify_oblex1_live_state import (
    EXPECTED_CORE,
    EXPECTED_FLAGS,
    TARGET_ID,
    TARGET_NAME,
    verify_live_state,
)


class FakeCollection:
    def __init__(self, row):
        self.row = row

    async def find_one(self, query):
        assert query == {"id": TARGET_ID}
        return self.row


def _row():
    return {
        "id": TARGET_ID,
        "name": TARGET_NAME,
        "reference_type": "monster",
        "review_status": "pending",
        "review_flags": list(EXPECTED_FLAGS),
        "canonical_id": None,
        "source_text_checksum": "sealed-source-checksum",
        "source_refs": [{"filename": "manual.pdf", "page": 6}],
        "attributes": dict(EXPECTED_CORE),
        "updated_at": "2026-09-21T21:22:13.540789Z",
    }


def test_verify_oblex1_live_state_accepts_exact_applied_repair():
    verified = asyncio.run(verify_live_state(FakeCollection(_row())))

    assert verified["id"] == TARGET_ID


def test_verify_oblex1_live_state_rejects_core_drift():
    row = _row()
    row["attributes"]["punti_ferita"] = "114 (10d12 + 50)"

    try:
        asyncio.run(verify_live_state(FakeCollection(row)))
    except RuntimeError as exc:
        assert "core mismatch" in str(exc)
    else:
        raise AssertionError("post-write verification must fail closed on core drift")
