import os

import pytest


# Keep the unit/in-process test suite deterministic and independent from real
# external credentials. These are inert test-only values; network calls are
# mocked by the tests that exercise provider behavior.
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("SEGMIND_API_KEY", "test-segmind-key")
os.environ.setdefault(
    "JWT_SECRET",
    "test-only-jwt-secret-for-tomoforge-ci",
)


@pytest.fixture(autouse=True)
def _disable_preload_recovery_during_tests(monkeypatch):
    """Prevent TestClient lifespan from reaching a real Supabase instance.

    Tests that explicitly exercise lifespan recovery can still monkeypatch
    server.resume_manual_preload_workers with their own implementation.
    """

    import services.preload as preload_mod

    async def _no_preload_recovery(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        preload_mod,
        "resume_manual_preload_workers",
        _no_preload_recovery,
    )

    # Most tests import server during collection. Patch that already-imported
    # compatibility symbol too; if server is reloaded later, it imports the
    # patched service function above.
    try:
        import server
    except ImportError:
        return

    monkeypatch.setattr(
        server,
        "resume_manual_preload_workers",
        _no_preload_recovery,
    )


# These suites exercise a running, paid external environment. They remain
# available to CI or a configured workspace, but must not be collected by the
# local configuration-only test run.
if os.getenv("RUN_INTEGRATION_TESTS") != "1":
    collect_ignore = [
        "tests/backend_test.py",
        "tests/test_premium_admin.py",
        "tests/test_public_endpoints.py",
    ]
