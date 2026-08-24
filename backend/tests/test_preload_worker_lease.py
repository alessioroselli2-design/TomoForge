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
import services.preload as preload_mod


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


# ---------------------------------------------------------------------------
# Test 4: a renewal stops when another worker replaces its lease
# ---------------------------------------------------------------------------

def test_lease_renewal_stops_after_ownership_is_lost(monkeypatch):
    """A renewal task must exit when its lease_id no longer matches the row."""
    first_sleep_started = asyncio.Event()
    release_first_sleep = asyncio.Event()

    async def _controlled_sleep(_delay):
        first_sleep_started.set()
        await release_first_sleep.wait()

    monkeypatch.setattr(
        preload_mod,
        "asyncio",
        SimpleNamespace(
            CancelledError=asyncio.CancelledError,
            sleep=_controlled_sleep,
        ),
    )

    original_lease_id = "first-worker-lease"
    replacement_lease_id = "recovered-worker-lease"
    original_expiry = 123
    job = _make_job(
        status="processing",
        lease_id=original_lease_id,
        lease_expires_at=original_expiry,
    )
    fake_db, collection = _fake_db(job)

    async def _exercise():
        renewal_task = asyncio.create_task(
            preload_mod.renew_manual_preload_lease(
                _USER_ID,
                job["id"],
                original_lease_id,
                db=fake_db,
            )
        )
        await first_sleep_started.wait()

        # Simulate recovery by another worker before the original worker's
        # first renewal attempt reaches the compare-and-set query.
        collection.rows[0]["lease_id"] = replacement_lease_id
        collection.rows[0]["lease_expires_at"] = 456
        release_first_sleep.set()

        # The coroutine should return normally after its guarded update misses.
        result = await asyncio.wait_for(renewal_task, timeout=1)
        return result

    assert asyncio.run(_exercise()) is None
    assert collection.update_matched_counts == [0], (
        "The old worker must not renew a lease it no longer owns"
    )
    assert collection.rows[0]["lease_id"] == replacement_lease_id
    assert collection.rows[0]["lease_expires_at"] == 456


# ---------------------------------------------------------------------------
# Test 5: a matching lease continues to renew
# ---------------------------------------------------------------------------

def test_lease_renewal_continues_while_ownership_matches(monkeypatch):
    """A renewal task must extend a lease while its lease_id remains current."""
    first_sleep_started = asyncio.Event()
    second_sleep_started = asyncio.Event()
    release_first_sleep = asyncio.Event()
    hold_second_sleep = asyncio.Event()
    sleep_calls = 0

    async def _controlled_sleep(_delay):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            first_sleep_started.set()
            await release_first_sleep.wait()
        else:
            second_sleep_started.set()
            await hold_second_sleep.wait()

    monkeypatch.setattr(
        preload_mod,
        "asyncio",
        SimpleNamespace(
            CancelledError=asyncio.CancelledError,
            sleep=_controlled_sleep,
        ),
    )

    lease_id = "current-worker-lease"
    original_expiry = 123
    job = _make_job(
        status="processing",
        lease_id=lease_id,
        lease_expires_at=original_expiry,
    )
    fake_db, collection = _fake_db(job)

    async def _exercise():
        renewal_task = asyncio.create_task(
            preload_mod.renew_manual_preload_lease(
                _USER_ID,
                job["id"],
                lease_id,
                db=fake_db,
            )
        )
        await first_sleep_started.wait()
        release_first_sleep.set()
        await second_sleep_started.wait()

        # The task is still alive in its next interval, proving the matching
        # lease did not cause the renewal loop to stop.
        assert not renewal_task.done()
        renewed_expiry = collection.rows[0]["lease_expires_at"]

        renewal_task.cancel()
        await asyncio.gather(renewal_task, return_exceptions=True)
        return renewed_expiry

    renewed_expiry = asyncio.run(_exercise())
    assert collection.update_matched_counts == [1]
    assert collection.rows[0]["lease_id"] == lease_id
    assert renewed_expiry > original_expiry


# ---------------------------------------------------------------------------
# Test 6: a transient renewal failure does not lose ownership
# ---------------------------------------------------------------------------

def test_lease_renewal_retries_after_transient_storage_failure(monkeypatch):
    """A failed renewal attempt must not stop later renewals for the same lease."""
    first_sleep_started = asyncio.Event()
    second_sleep_started = asyncio.Event()
    third_sleep_started = asyncio.Event()
    release_first_sleep = asyncio.Event()
    release_second_sleep = asyncio.Event()
    hold_third_sleep = asyncio.Event()
    sleep_calls = 0

    async def _controlled_sleep(_delay):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            first_sleep_started.set()
            await release_first_sleep.wait()
        elif sleep_calls == 2:
            second_sleep_started.set()
            await release_second_sleep.wait()
        else:
            third_sleep_started.set()
            await hold_third_sleep.wait()

    monkeypatch.setattr(
        preload_mod,
        "asyncio",
        SimpleNamespace(
            CancelledError=asyncio.CancelledError,
            sleep=_controlled_sleep,
        ),
    )

    lease_id = "original-worker-lease"
    job = _make_job(
        status="processing",
        lease_id=lease_id,
        lease_expires_at=123,
    )
    fake_db, collection = _fake_db(job)
    original_update_one = collection.update_one
    update_calls = 0

    async def _fail_once_then_update(query, update):
        nonlocal update_calls
        update_calls += 1
        if update_calls == 1:
            raise RuntimeError("temporary storage outage")
        return await original_update_one(query, update)

    monkeypatch.setattr(collection, "update_one", _fail_once_then_update)

    async def _exercise():
        renewal_task = asyncio.create_task(
            preload_mod.renew_manual_preload_lease(
                _USER_ID,
                job["id"],
                lease_id,
                db=fake_db,
            )
        )
        await first_sleep_started.wait()
        release_first_sleep.set()
        await second_sleep_started.wait()

        # The first update failed, but the renewal loop must remain alive.
        assert not renewal_task.done()
        release_second_sleep.set()
        await third_sleep_started.wait()

        renewal_task.cancel()
        await asyncio.gather(renewal_task, return_exceptions=True)

    asyncio.run(_exercise())
    assert update_calls == 2, "The renewal loop must attempt a later renewal"
    assert collection.update_matched_counts == [1], (
        "The later renewal must succeed against the original lease"
    )
    assert collection.rows[0]["lease_id"] == lease_id, (
        "A transient storage failure must not change lease ownership"
    )
    assert collection.rows[0]["lease_expires_at"] > 123


# ---------------------------------------------------------------------------
# Test 7: the worker stops after losing ownership during a chunk
# ---------------------------------------------------------------------------

def test_worker_stops_after_mid_run_lease_ownership_loss(monkeypatch, tmp_path):
    """A lost lease must stop the worker before another chunk or checkpoint."""
    import services.library as lib_mod

    source = tmp_path / "Manuale.pdf"
    source.write_bytes(b"manual")
    original_lease_id = "first-worker-lease"
    replacement_lease_id = "recovered-worker-lease"
    job = _make_job(
        status="processing",
        lease_id=original_lease_id,
        lease_expires_at=123,
    )
    fake_db, collection = _fake_db(job)
    update_queries = []
    lease_loss_detected = asyncio.Event()
    renewal_sleep_started = asyncio.Event()
    release_renewal_sleep = asyncio.Event()
    claim_calls = 0
    import_calls = []

    async def _controlled_sleep(_delay):
        renewal_sleep_started.set()
        await release_renewal_sleep.wait()

    monkeypatch.setattr(
        preload_mod,
        "asyncio",
        SimpleNamespace(
            CancelledError=asyncio.CancelledError,
            Event=asyncio.Event,
            create_task=asyncio.create_task,
            gather=asyncio.gather,
            sleep=_controlled_sleep,
        ),
    )
    monkeypatch.setattr(preload_mod, "MANUAL_PRELOAD_LEASE_SECONDS", 3)
    monkeypatch.setattr(preload_mod, "MANUAL_PRELOAD_PAGE_BATCH_SIZE", 1)
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 2)
    monkeypatch.setattr(lib_mod, "manual_requires_ocr", lambda _filename: False)
    monkeypatch.setattr(lib_mod, "manual_source_duplicate_of", lambda _filename, _manuals: None)

    async def _claim_once(_user_id, *, db=None):
        nonlocal claim_calls
        claim_calls += 1
        if claim_calls == 1:
            return copy.deepcopy(job)
        raise AssertionError("The worker must not claim another chunk after losing ownership")

    monkeypatch.setattr(preload_mod, "claim_next_manual_preload_job", _claim_once)

    async def _import_chunk(*_args, **_kwargs):
        import_calls.append(True)
        await renewal_sleep_started.wait()
        release_renewal_sleep.set()
        await lease_loss_detected.wait()
        return server.ReferenceImportResult(
            imported=1,
            updated=0,
            flagged_for_review=0,
            skipped=0,
            sources=[{"filename": source.name, "pages_needing_ocr": []}],
        )

    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", _import_chunk)
    original_update_one = collection.update_one

    async def _replace_lease_on_renewal(query, update):
        update_queries.append((query, update))
        if query.get("lease_id") == original_lease_id and not lease_loss_detected.is_set():
            collection.rows[0]["lease_id"] = replacement_lease_id
            collection.rows[0]["lease_expires_at"] = 456
            lease_loss_detected.set()
            return server.UpdateResult(0)
        return await original_update_one(query, update)

    monkeypatch.setattr(collection, "update_one", _replace_lease_on_renewal)

    asyncio.run(preload_mod.run_manual_preload_worker(_USER_ID, db=fake_db))

    assert claim_calls == 1
    assert import_calls == [True]
    assert len(update_queries) == 1
    assert update_queries[0][0]["lease_id"] == original_lease_id
    assert collection.rows[0]["lease_id"] == replacement_lease_id
    assert collection.rows[0]["lease_expires_at"] == 456


# ---------------------------------------------------------------------------
# Test 8: the process-local worker registry prevents duplicate starts
# ---------------------------------------------------------------------------

def test_start_worker_is_noop_for_an_active_user(monkeypatch):
    """A second start request must not create another worker task."""
    user_id = "active-worker-user"
    worker_started = asyncio.Event()
    release_worker = asyncio.Event()
    created_tasks = []

    async def _fake_worker(_user_id, *, db=None):
        worker_started.set()
        await release_worker.wait()

    original_create_task = asyncio.create_task

    def _create_task(coro):
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(preload_mod, "run_manual_preload_worker", _fake_worker)
    monkeypatch.setattr(preload_mod.asyncio, "create_task", _create_task)

    async def _exercise():
        preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS.discard(user_id)
        try:
            preload_mod.start_manual_preload_worker(user_id)
            await worker_started.wait()

            preload_mod.start_manual_preload_worker(user_id)

            assert len(created_tasks) == 1
            assert user_id in preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS
        finally:
            release_worker.set()
            await asyncio.gather(*created_tasks, return_exceptions=True)
            preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS.discard(user_id)

    asyncio.run(_exercise())


# ---------------------------------------------------------------------------
# Test 9: a finished worker clears the registry and can be started again
# ---------------------------------------------------------------------------

def test_start_worker_after_previous_worker_finishes(monkeypatch):
    """The worker cleanup path must permit a later start for the same user."""
    user_id = "reusable-worker-user"
    first_claim_started = asyncio.Event()
    release_first_claim = asyncio.Event()
    second_claim_started = asyncio.Event()
    claim_count = 0
    created_tasks = []

    async def _fake_claim(_user_id, *, db=None):
        nonlocal claim_count
        claim_count += 1
        if claim_count == 1:
            first_claim_started.set()
            await release_first_claim.wait()
        else:
            second_claim_started.set()
        return None

    original_create_task = asyncio.create_task

    def _create_task(coro):
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(preload_mod, "claim_next_manual_preload_job", _fake_claim)
    monkeypatch.setattr(preload_mod.asyncio, "create_task", _create_task)

    async def _exercise():
        preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS.discard(user_id)
        try:
            preload_mod.start_manual_preload_worker(user_id)
            await first_claim_started.wait()

            preload_mod.start_manual_preload_worker(user_id)
            assert len(created_tasks) == 1

            release_first_claim.set()
            await created_tasks[0]
            assert user_id not in preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS

            preload_mod.start_manual_preload_worker(user_id)
            await second_claim_started.wait()
            assert len(created_tasks) == 2
            await created_tasks[1]
        finally:
            release_first_claim.set()
            await asyncio.gather(*created_tasks, return_exceptions=True)
            preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS.discard(user_id)

    asyncio.run(_exercise())


# ---------------------------------------------------------------------------
# Test 10: a crashed worker clears the registry and can be started again
# ---------------------------------------------------------------------------

def test_start_worker_after_previous_worker_crashes(monkeypatch):
    """A worker exception must not permanently block a later start."""
    user_id = "crashed-worker-user"
    first_worker_started = asyncio.Event()
    second_worker_started = asyncio.Event()
    claim_count = 0
    created_tasks = []

    async def _fake_claim(_user_id, *, db=None):
        nonlocal claim_count
        claim_count += 1
        if claim_count == 1:
            first_worker_started.set()
            raise RuntimeError("transient preload failure")
        second_worker_started.set()
        return None

    original_create_task = asyncio.create_task

    def _create_task(coro):
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(preload_mod, "claim_next_manual_preload_job", _fake_claim)
    monkeypatch.setattr(preload_mod.asyncio, "create_task", _create_task)

    async def _exercise():
        preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS.discard(user_id)
        try:
            preload_mod.start_manual_preload_worker(user_id)
            await first_worker_started.wait()

            try:
                await created_tasks[0]
            except RuntimeError as exc:
                assert str(exc) == "transient preload failure"
            else:
                raise AssertionError("The first worker should have crashed")

            assert user_id not in preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS

            preload_mod.start_manual_preload_worker(user_id)
            await second_worker_started.wait()
            assert len(created_tasks) == 2
            await created_tasks[1]
        finally:
            await asyncio.gather(*created_tasks, return_exceptions=True)
            preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS.discard(user_id)

    asyncio.run(_exercise())
