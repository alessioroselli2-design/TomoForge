import asyncio

from core.db import MemoryCollection
from scripts.cleanup_corrupted_monster_names import (
    EXPECTED_TARGET_COUNT,
    EXPECTED_TARGET_IDS_MD5,
    PURGE_READY_FLAG,
    TARGETS,
    _ids_md5,
    _isolate,
    _purge,
    _state,
)
from services.ocr_semantic_gates import (
    CORRUPTED_ENTITY_NAME_FLAG,
    monster_identity_sanity_flags,
)


def _live_like_row(target: dict[str, str]) -> dict:
    return {
        **target,
        "reference_type": "monster",
        "review_status": "verified",
        "review_flags": [],
        "canonical_id": None,
    }


def test_cleanup_target_set_is_exactly_four_and_fingerprint_is_sealed():
    assert len(TARGETS) == EXPECTED_TARGET_COUNT == 4
    assert _ids_md5(TARGETS) == EXPECTED_TARGET_IDS_MD5
    assert len({target["id"] for target in TARGETS}) == 4


def test_all_sealed_names_fail_monster_identity_sanity_gate():
    for target in TARGETS:
        assert CORRUPTED_ENTITY_NAME_FLAG in monster_identity_sanity_flags(
            target["name"]
        )


def test_state_requires_both_isolation_flags_for_needs_review():
    verified = _live_like_row(TARGETS[0])
    assert _state(verified) == "verified"

    isolated = {
        **verified,
        "review_status": "needs_review",
        "review_flags": [CORRUPTED_ENTITY_NAME_FLAG, PURGE_READY_FLAG],
    }
    assert _state(isolated) == "isolated"

    incomplete = {
        **verified,
        "review_status": "needs_review",
        "review_flags": [CORRUPTED_ENTITY_NAME_FLAG],
    }
    assert _state(incomplete) == "unexpected"


def test_isolate_is_reversible_idempotent_and_preserves_existing_flags():
    collection = MemoryCollection()
    rows = []
    for target in TARGETS:
        row = _live_like_row(target)
        row["review_flags"] = ["legacy_note"]
        rows.append(row)
    collection.rows = [dict(row) for row in rows]

    changed = asyncio.run(_isolate(collection, rows))
    assert changed == 4

    for row in collection.rows:
        assert row["review_status"] == "needs_review"
        assert "legacy_note" in row["review_flags"]
        assert CORRUPTED_ENTITY_NAME_FLAG in row["review_flags"]
        assert PURGE_READY_FLAG in row["review_flags"]
        assert row.get("updated_at") is not None

    changed_again = asyncio.run(_isolate(collection, collection.rows))
    assert changed_again == 0


def test_purge_refuses_any_nonisolated_target_before_delete():
    collection = MemoryCollection()
    rows = [_live_like_row(target) for target in TARGETS]
    collection.rows = [dict(row) for row in rows]

    try:
        asyncio.run(_purge(collection, rows))
    except RuntimeError as exc:
        assert "must be isolated first" in str(exc)
    else:
        raise AssertionError("purge must fail before isolation")

    assert len(collection.rows) == 4
