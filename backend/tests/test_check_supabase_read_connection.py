from types import SimpleNamespace

from scripts.check_supabase_read_connection import run_diagnostic


class _FakeQuery:
    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=[{"id": "synthetic"}])


class _FakeClient:
    def table(self, name):
        assert name == "private_reference_sources"
        return _FakeQuery()


def _run(env):
    calls = []
    output = []

    def fake_create_client(url, key):
        calls.append((url, key))
        return _FakeClient()

    rc = run_diagnostic(
        environ=env,
        create_client_fn=fake_create_client,
        emit=output.append,
    )
    return rc, calls, output


def test_missing_anon_key_is_non_blocking_and_backend_stays_service_role_only():
    rc, calls, output = _run(
        {
            "SUPABASE_URL": "https://synthetic.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "synthetic-service-role",
        }
    )

    assert rc == 0
    assert calls == [("https://synthetic.supabase.co", "synthetic-service-role")]
    assert "anon_key_result=missing_optional_non_blocking" in output
    assert "backend_privilege_source=service_role_only" in output
    assert "connection_result=read_ok" in output


def test_all_three_keys_complete_pass_without_privilege_mix():
    rc, calls, output = _run(
        {
            "SUPABASE_URL": "https://synthetic.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "synthetic-service-role",
            "SUPABASE_ANON_KEY": "synthetic-anon",
        }
    )

    assert rc == 0
    assert calls == [("https://synthetic.supabase.co", "synthetic-service-role")]
    assert "anon_key_result=present_not_used_for_backend_read" in output
    assert "backend_privilege_source=service_role_only" in output
    assert "connection_result=read_ok" in output


def test_anon_key_never_substitutes_for_missing_service_role():
    calls = []
    output = []

    def fake_create_client(url, key):
        calls.append((url, key))
        return _FakeClient()

    rc = run_diagnostic(
        environ={
            "SUPABASE_URL": "https://synthetic.supabase.co",
            "SUPABASE_ANON_KEY": "synthetic-anon",
        },
        create_client_fn=fake_create_client,
        emit=output.append,
    )

    assert rc == 2
    assert calls == []
    assert "missing_required=SUPABASE_SERVICE_ROLE_KEY" in output
    assert "backend_privilege_source=service_role_required_no_fallback" in output
