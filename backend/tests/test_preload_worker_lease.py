"""Regression tests for the preload worker lease-claim concurrency gate.

Verifies that claim_next_manual_preload_job:
- allows exactly one of two concurrent callers to claim a queued job,
- does not re-claim a job whose lease has not yet expired,
- re-claims (recovers) a job whose lease has expired.
"""

import asyncio
import copy
import time
import uuid
from types import SimpleNamespace

import server


_USER_ID = "lease-test-user"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(status="queued", lease_id="", lease_expires_at=0):
    """Return a minimal manual-preload job record."""
    return {
        "id": f"job-{uuid.uuid4().hex}",
        "user_id": _USER_ID,
        "filename": "Manuale.pdf",
        "status": status,
        "current_page": 1,
        "attempt_count": 0,
        "last_error": "",
        "lease_id": lease_id,
        "lease_expires_at": lease_expires_at,
        "updated_at": "2024-01-01T00:00:00+00:00",
    }


class _SpyCollection(server.MemoryCollection):
    """MemoryCollection that records the matched_count of every update_one call."""

    def __init__(self):
        super().__init__()
        self.update_matched_counts: list[int] = []

    async def update_one(self, query, update):
        result = await super().update_one(query, update)
        self.update_matched_counts.append(result.matched_count)
        return result


def _fake_db(job: dict):
    """Build a fake db namespace backed by a _SpyCollection seeded with *job*."""
    collection = _SpyCollection()
    collection.rows.append(copy.deepcopy(job))
    return SimpleNamespace(private_manual_import_jobs=collection), collection


def _patch_claim(monkeypatch, fake_db, collection):
    """Wire monkeypatches so claim_next_manual_preload_job uses fake_db.

    - private_manual_import_jobs is imported lazily inside the function body, so
      patch it directly on the services.library module.
    - db is patched on services.preload directly (claim_next_manual_preload_job
      uses it to access private_manual_import_jobs collection).

    The reader snapshots rows BEFORE yielding so that both concurrent callers
    capture the pre-claim (queued) state and both then attempt update_one.
    This is the critical difference from a naive sleep-then-read approach: it
    guarantees the race reaches the atomic compare-and-swap guard.
    """
    import services.library as lib_mod
    async def _read_jobs(user_id, *, db=None):
        # Snapshot BEFORE the cooperative yield so every concurrent caller
        # captures the same pre-claim state.  The yield that follows lets the
        # event loop interleave callers so both construct their candidate lists
        # from the queued snapshot before either one runs update_one.
        snapshot = [
            copy.deepcopy(row)
            for row in collection.rows
            if row.get("user_id") == user_id
        ]
        await asyncio.sleep(0)
        return snapshot

    monkeypatch.setattr(lib_mod, "private_manual_import_jobs", _read_jobs)


# ---------------------------------------------------------------------------
# Test 1: two concurrent workers race for the same queued job
# ---------------------------------------------------------------------------

def test_only_one_worker_claims_a_queued_job_when_two_race(monkeypatch):
    """Exactly one of two concurrent claim attempts must succeed; the other gets None.

    Both coroutines snapshot the job as 'queued', then yield so the event loop
    interleaves them.  Both therefore attempt the guarded update_one.  Because
    update_one is atomic (no internal awaits), the first caller's write changes
    the status to 'processing'; the second caller's predicate (status='queued'
    OR expired-processing) no longer matches, so matched_count == 0.

    This test fails if the update predicate is weakened to only id/user_id,
    because then both callers would match and both update_matched_counts entries
    would be 1 (both workers would claim the same job).
    """
    job = _make_job(status="queued")
    fake_db, collection = _fake_db(job)
    _patch_claim(monkeypatch, fake_db, collection)

    async def _two_concurrent():
        return await asyncio.gather(
            server.claim_next_manual_preload_job(_USER_ID, db=fake_db),
            server.claim_next_manual_preload_job(_USER_ID, db=fake_db),
        )

    r1, r2 = asyncio.run(_two_concurrent())

    # Both callers must have reached and attempted update_one.
    assert len(collection.update_matched_counts) == 2, (
        f"Expected both callers to attempt update_one; got {collection.update_matched_counts}"
    )
    # Exactly one update succeeded; the other was blocked by the status guard.
    assert sorted(collection.update_matched_counts) == [0, 1], (
        f"Expected one match and one miss; got {collection.update_matched_counts}. "
        "If both entries are 1, the status/expiry predicate in update_one is missing."
    )

    winners = [r for r in (r1, r2) if r is not None]
    misses  = [r for r in (r1, r2) if r is None]

    assert len(winners) == 1, (
        f"Expected exactly 1 winner, got {len(winners)}. r1={r1}, r2={r2}"
    )
    assert len(misses) == 1, "Expected exactly 1 non-claiming caller"

    winner = winners[0]
    assert winner["status"] == "processing", "Winner must hold a processing lease"
    assert winner["lease_id"] != "", "Winner lease_id must be set"
    assert winner["lease_expires_at"] > int(time.time()), "Winner lease must be future-dated"

    # The database row itself must be updated exactly once.
    assert len(collection.rows) == 1, "No duplicate rows should have been created"
    stored = collection.rows[0]
    assert stored["status"] == "processing", "Stored row must reflect the claimed state"
    assert stored["lease_id"] == winner["lease_id"], "Stored lease must match the returned job"


# ---------------------------------------------------------------------------
# Test 2: an active (non-expired) lease blocks a second worker
# ---------------------------------------------------------------------------

def test_active_lease_blocks_second_claim(monkeypatch):
    """A job already held by a live lease must not be stolen by another worker.

    The update_one query requires either status='queued' or
    (status='processing' AND lease_expires_at < now).  A future-dated lease
    fails both conditions, so matched_count == 0.
    """
    future_expiry = int(time.time()) + 3600
    job = _make_job(
        status="processing",
        lease_id="first-worker-lease",
        lease_expires_at=future_expiry,
    )
    fake_db, collection = _fake_db(job)
    _patch_claim(monkeypatch, fake_db, collection)

    result = asyncio.run(server.claim_next_manual_preload_job(_USER_ID, db=fake_db))

    assert result is None, "A job with an unexpired lease must not be re-claimed"

    stored = collection.rows[0]
    assert stored["lease_id"] == "first-worker-lease", (
        "Original lease must remain untouched after a failed claim attempt"
    )
    assert stored["lease_expires_at"] == future_expiry, (
        "Lease expiry must not be changed by a failed claim attempt"
    )


# ---------------------------------------------------------------------------
# Test 3: an expired lease IS reclaimable (recovery path)
# ---------------------------------------------------------------------------

def test_expired_lease_is_reclaimable(monkeypatch):
    """A job stuck in 'processing' with an expired lease must be claimable by a new worker.

    Workers that crash or are killed leave jobs with lease_expires_at in the
    past.  claim_next_manual_preload_job must recover them by matching the
    (status='processing' AND lease_expires_at < now) branch of the $or guard.
    """
    past_expiry = int(time.time()) - 30
    job = _make_job(
        status="processing",
        lease_id="dead-worker-lease",
        lease_expires_at=past_expiry,
    )
    fake_db, collection = _fake_db(job)
    _patch_claim(monkeypatch, fake_db, collection)

    result = asyncio.run(server.claim_next_manual_preload_job(_USER_ID, db=fake_db))

    assert result is not None, "An expired-lease job must be reclaimable"
    assert result["status"] == "processing", "Recovered job must enter processing state"
    assert result["lease_id"] != "dead-worker-lease", (
        "A fresh lease_id must replace the stale one"
    )
    assert result["lease_id"] != "", "New lease_id must be non-empty"
    assert result["lease_expires_at"] > int(time.time()), (
        "New lease expiry must be set to a future timestamp"
    )
