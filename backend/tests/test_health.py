from fastapi.testclient import TestClient

from server import app


def test_health_reports_configuration_without_secrets():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert set(payload["services"]) == {"supabase", "supabase_auth", "openai", "gemini", "segmind", "jwt", "stripe"}