"""CORS policy tests — verifies the origin allowlist and credential rules.

Allowed origins:
  - Values from CORS_ORIGINS env var (default: localhost:5000 and 127.0.0.1:5000)
  - Any https://*.replit.dev domain (via allow_origin_regex)

Denied origins:
  - Any origin not in the above sets (e.g. https://evil.example)

Credentialed requests (with cookie/Authorization) must never be allowed from an
arbitrary origin — FastAPI/Starlette must not echo the origin back with
Access-Control-Allow-Credentials: true for unknown origins.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    """Fresh app with the default CORS_ORIGINS (localhost:5000)."""
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    # Re-import app so the middleware picks up the patched env
    import importlib
    import server as server_module
    importlib.reload(server_module)
    from server import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def client_env(monkeypatch):
    """App with a custom CORS_ORIGINS that includes https://app.example."""
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example,http://localhost:5000")
    import importlib
    import server as server_module
    importlib.reload(server_module)
    from server import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestAllowedOrigins:
    def test_localhost_origin_is_allowed(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5000"

    def test_loopback_origin_is_allowed(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://127.0.0.1:5000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5000"

    def test_replit_dev_subdomain_is_allowed(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "https://myapp.replit.dev",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "https://myapp.replit.dev"

    def test_replit_dev_subdomain_with_prefix_is_allowed(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "https://abc123--5000.local.webcontainer-api.io.replit.dev",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == (
            "https://abc123--5000.local.webcontainer-api.io.replit.dev"
        )

    def test_custom_env_origin_is_allowed(self, client_env):
        resp = client_env.options(
            "/api/health",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "https://app.example"


class TestDeniedOrigins:
    def test_arbitrary_origin_is_denied(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        origin_header = resp.headers.get("access-control-allow-origin", "")
        assert origin_header != "https://evil.example", (
            "Arbitrary origin must not be reflected in Access-Control-Allow-Origin"
        )
        assert origin_header != "*", (
            "Wildcard must not be returned when credentials are enabled"
        )

    def test_arbitrary_origin_does_not_get_credentials_header(self, client):
        """Credentialed request from an unknown origin must not receive allow-credentials."""
        resp = client.get(
            "/api/health",
            headers={
                "Origin": "https://evil.example",
                "Cookie": "session_token=fake",
            },
        )
        cred_header = resp.headers.get("access-control-allow-credentials", "")
        origin_header = resp.headers.get("access-control-allow-origin", "")
        # Both being set for an unknown origin would be the vulnerability
        assert not (
            cred_header.lower() == "true" and origin_header == "https://evil.example"
        ), (
            "Must not echo arbitrary origin together with Access-Control-Allow-Credentials: true"
        )

    def test_http_replit_dev_not_matched_by_regex(self, client):
        """Only https://*.replit.dev should match — plain http must not."""
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://myapp.replit.dev",
                "Access-Control-Request-Method": "GET",
            },
        )
        # http variant is not in CORS_ORIGINS default and regex requires https
        origin_header = resp.headers.get("access-control-allow-origin", "")
        assert origin_header != "http://myapp.replit.dev"
