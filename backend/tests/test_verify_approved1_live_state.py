import asyncio

from scripts.verify_approved1_live_state import (
    EXPECTED_CORE,
    EXPECTED_FLAGS,
    TARGET_CHECKSUM,
    TARGET_ID,
    TARGET_NAME,
    verify_live_state,
)


class _Collection:
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
        "review_flags": EXPECTED_FLAGS,
        "source_text_checksum": TARGET_CHECKSUM,
        "source_refs": [{"filename": "manual.pdf", "page": 43}],
        "canonical_id": None,
        "attributes": EXPECTED_CORE,
        "updated_at": "2026-09-20T12:57:12.999999+00:00",
    }


def test_verify_live_state_accepts_only_exact_confirmed_repair():
    row = _row()

    verified = asyncio.run(verify_live_state(_Collection(row)))

    assert verified is row


def test_verify_live_state_rejects_core_drift():
    row = _row()
    row["attributes"] = {**EXPECTED_CORE, "punti_ferita": "1"}

    try:
        asyncio.run(verify_live_state(_Collection(row)))
    except RuntimeError as exc:
        assert "core mismatch" in str(exc)
    else:
        raise AssertionError("post-write verification must fail closed on core drift")
