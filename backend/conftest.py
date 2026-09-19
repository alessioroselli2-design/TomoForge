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


_REAL_PRELOAD_RECOVERY_TESTS = {
    "test_startup_reclaims_only_expired_preload_leases",
    "test_startup_requeues_legacy_translation_consent_job_for_processing",
    "test_startup_requeues_completed_manual_when_its_parser_revision_changes",
}


@pytest.fixture(autouse=True)
def _isolate_preload_recovery(monkeypatch, request):
    """Keep TestClient startup away from real Supabase during unit tests.

    The dedicated preload-recovery tests are explicitly exempt so they still
    exercise the real recovery implementation with their injected fake DB.
    """

    import server
    import services.preload as preload_mod

    if request.node.name in _REAL_PRELOAD_RECOVERY_TESTS:
        monkeypatch.setattr(
            server,
            "resume_manual_preload_workers",
            preload_mod.resume_manual_preload_workers,
        )
        return

    async def _no_preload_recovery(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        preload_mod,
        "resume_manual_preload_workers",
        _no_preload_recovery,
    )
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
