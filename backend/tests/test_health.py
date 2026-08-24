import asyncio

from fastapi.testclient import TestClient

from server import app
import server


def test_health_reports_configuration_without_secrets():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert set(payload["services"]) == {"supabase", "supabase_auth", "openai", "gemini", "segmind", "jwt", "stripe"}


def test_lifespan_seeds_and_recovers_before_shutdown(monkeypatch):
    events = []

    async def fake_seed():
        events.append("seed")

    async def fake_resume():
        events.append("resume")

    monkeypatch.setattr(server, "seed_mock_data", fake_seed)
    monkeypatch.setattr(server, "resume_manual_preload_workers", fake_resume)
    monkeypatch.setattr("core.config.MOCK_DATA", True)

    async def exercise_lifespan():
        async with server.lifespan(app):
            events.append("running")
        events.append("shutdown")

    asyncio.run(exercise_lifespan())

    assert events == ["seed", "resume", "running", "shutdown"]