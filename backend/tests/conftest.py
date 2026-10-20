"""Keep CI tests isolated from startup-time Supabase network calls.

The legacy app resumes manual preload workers in FastAPI lifespan startup.
Those workers must not contact a live (or dummy) Supabase during unit tests;
individual preload tests can still invoke their own target functions.
"""

import pytest


@pytest.fixture(autouse=True)
def isolate_automatic_preload_startup(monkeypatch):
    import server
    import services.preload as preload

    original_resume = preload.resume_manual_preload_workers

    async def skip_remote_preload(*, db=None):
        # Lifespan invokes recovery without an injected DB: do not connect
        # to a remote database during CI. Recovery unit tests pass their own
        # in-memory db and must exercise the original implementation.
        if db is not None:
            return await original_resume(db=db)
        return None

    monkeypatch.setattr(preload, "resume_manual_preload_workers", skip_remote_preload)
    monkeypatch.setattr(server, "resume_manual_preload_workers", skip_remote_preload)
