import asyncio
import base64
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import server

import core.auth as core_auth_mod
import core.providers as core_providers_mod
import routers.auth as auth_router_mod
import services.media as services_media


class FakeCards:
    def __init__(self):
        self.documents = []

    async def insert_one(self, document):
        self.documents.append(document)


class FakeFiles:
    def __init__(self):
        self.documents = []

    async def insert_one(self, document):
        self.documents.append(document)


class FakeDatabase:
    def __init__(self):
        self.cards = FakeCards()
        self.files = FakeFiles()


def test_card_creation_keeps_owner_foil_frame_and_appearance(monkeypatch):
    fake_db = FakeDatabase()
    user = server.User(user_id="user_123", email="mage@example.com", name="Mage")

    card = asyncio.run(server.create_card(
        server.CardCreate(
            type="spell",
            name="Lancia di luce",
            frame="rainbow",
            appearance=server.CardAppearance(
                title_effect="silver",
                title_shadow=False,
                description_opacity=0.8,
                text_panel_color="#0b1d31",
                text_color="#dbeafe",
                front_background_start="#0b1d31",
                front_background_end="#581c87",
                front_background_gradient=True,
                title_custom_color_enabled=True,
                title_custom_color="#67e8f9",
                frame_custom_color_enabled=True,
                frame_custom_color="#f43f5e",
            ),
        ),
        user,
        db=fake_db,
    ))

    assert card.user_id == user.user_id
    assert card.frame == "rainbow"
    assert card.appearance.title_effect == "silver"
    assert card.appearance.title_shadow is False
    assert card.appearance.description_opacity == 0.8
    assert card.appearance.text_panel_color == "#0b1d31"
    assert card.appearance.text_color == "#dbeafe"
    assert card.appearance.front_background_gradient is True
    assert card.appearance.front_background_end == "#581c87"
    assert card.appearance.title_custom_color == "#67e8f9"
    assert card.appearance.frame_custom_color == "#f43f5e"
    assert fake_db.cards.documents[0]["name"] == "Lancia di luce"
    assert fake_db.cards.documents[0]["appearance"]["title_effect"] == "silver"
    assert fake_db.cards.documents[0]["appearance"]["text_color"] == "#dbeafe"
    assert fake_db.cards.documents[0]["appearance"]["front_background_gradient"] is True


def test_file_record_is_created_after_storage_upload(monkeypatch):
    fake_db = FakeDatabase()
    monkeypatch.setattr(services_media, "put_object", lambda path, data, content_type: path)

    saved_path = asyncio.run(server.save_file(
        "uploads/user_123/card.png", b"image-bytes", "image/png", "user_123", "card.png", db=fake_db
    ))

    assert saved_path == "uploads/user_123/card.png"
    assert fake_db.files.documents[0]["user_id"] == "user_123"
    assert fake_db.files.documents[0]["content_type"] == "image/png"


def test_artwork_cleanup_is_a_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(services_media, "ARTWORK_CLEANUP_ENABLED", False)

    result = asyncio.run(server.cleanup_artwork(b"original-artwork", "image/jpeg"))

    assert result == (b"original-artwork", "image/jpeg")


def test_artwork_cleanup_removes_marks_before_the_image_is_saved(monkeypatch):
    fake_db = FakeDatabase()
    calls = {}
    cleaned_bytes = b"cleaned-png-artwork"

    class FakeImages:
        async def edit(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(data=[SimpleNamespace(
                b64_json=base64.b64encode(cleaned_bytes).decode("ascii")
            )])

    monkeypatch.setattr(services_media, "ARTWORK_CLEANUP_ENABLED", True)
    monkeypatch.setattr(services_media, "require_openai", lambda: SimpleNamespace(images=FakeImages()))
    monkeypatch.setattr(services_media, "put_object", lambda path, data, content_type: path)

    saved_path, cleanup_notice = asyncio.run(server.save_artwork(
        "artwork/user_123/generated.jpg",
        b"segmind-jpeg-artwork",
        "image/jpeg",
        "user_123",
        "segmind-generated.jpg",
        cleanup=True,
        db=fake_db,
    ))

    assert calls["model"] == server.ARTWORK_CLEANUP_MODEL
    assert calls["image"].read() == b"segmind-jpeg-artwork"
    assert "signature" in calls["prompt"]
    assert "watermark" in calls["prompt"]
    assert saved_path == "artwork/user_123/generated.png"
    assert cleanup_notice is None
    assert fake_db.files.documents[0]["content_type"] == "image/png"
    assert fake_db.files.documents[0]["original_filename"] == "segmind-generated.png"


def test_gemini_content_response_is_mapped_to_card_fields(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{
                "text": '{"name":"Nebbia runica","description":"Una nebbia protettiva.","story":"Nata tra le rovine.","attributes":{"livello":"2"}}'
            }]}}]}

    request_data = {}

    def fake_post(url, **kwargs):
        request_data["url"] = url
        request_data.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(server.requests, "post", fake_post)
    user = server.User(user_id="user_123", email="mage@example.com", name="Mage", premium_manual=True)

    result = asyncio.run(server.generate_content(
        server.GenerateContentInput(type="spell", prompt="Una nebbia protettiva"),
        user,
        gemini_key="test-gemini-key",
    ))

    assert result == {
        "name": "Nebbia runica",
        "description": "Una nebbia protettiva.",
        "story": "Nata tra le rovine.",
        "attributes": {"livello": "2"},
        "source": "ai_generated",
        "source_status": "unavailable",
        "source_message": "Il contenuto richiesto non è disponibile come fonte verificata nella tua biblioteca; il testo generato non è una regola certa.",
    }
    assert request_data["url"].endswith("/models/gemini-2.0-flash:generateContent")
    assert request_data["headers"]["x-goog-api-key"] == "test-gemini-key"


def test_segmind_image_response_is_saved_as_card_artwork(monkeypatch):
    class FakeResponse:
        headers = {"content-type": "image/jpeg"}
        content = b"segmind-image-bytes"

        def raise_for_status(self):
            return None

    fake_db = FakeDatabase()
    request_data = {}
    cleanup_calls = []

    def fake_post(url, **kwargs):
        request_data["url"] = url
        request_data.update(kwargs)
        return FakeResponse()

    async def fake_cleanup(data, content_type):
        cleanup_calls.append((data, content_type))
        return b"cleaned-image-bytes", "image/png"

    monkeypatch.setattr(services_media, "put_object", lambda path, data, content_type: path)
    monkeypatch.setattr(services_media, "cleanup_artwork", fake_cleanup)
    monkeypatch.setattr(server.requests, "post", fake_post)
    user = server.User(user_id="user_123", email="mage@example.com", name="Mage", premium_manual=True)

    result = asyncio.run(server.generate_image(
        server.GenerateImageInput(type="spell", prompt="Una fenice di ossidiana", cleanup=True),
        user,
        segmind_key="test-key",
        db=fake_db,
    ))

    assert request_data["url"].endswith("/flux-dev")
    assert request_data["headers"]["x-api-key"] == "test-key"
    assert request_data["json"]["aspect_ratio"] == "2:3"
    assert request_data["json"]["samples"] == 1
    assert request_data["json"]["guidance"] == 3.5
    assert request_data["json"]["steps"] == 25
    assert request_data["json"]["prompt_strength"] == 0.8
    assert request_data["json"]["output_format"] == "webp"
    assert request_data["json"]["output_quality"] == 85
    prompt = request_data["json"]["prompt"]
    assert "depicting: Una fenice di ossidiana" in prompt
    assert "not a card design" in prompt
    assert "never render them as writing" in prompt
    assert "no typography, words, letters, numbers, readable runes" in prompt
    assert cleanup_calls == [(b"segmind-image-bytes", "image/jpeg")]
    assert result["artwork_path"].endswith(".png")
    assert fake_db.files.documents[0]["content_type"] == "image/png"
    assert fake_db.files.documents[0]["original_filename"] == "segmind-generated.png"


def test_generated_artwork_is_saved_with_notice_when_cleanup_fails(monkeypatch):
    class FakeResponse:
        headers = {"content-type": "image/jpeg"}
        content = b"segmind-image-bytes"

        def raise_for_status(self):
            return None

    async def failing_cleanup(data, content_type):
        raise RuntimeError("image cleanup unavailable")

    fake_db = FakeDatabase()
    monkeypatch.setattr(services_media, "put_object", lambda path, data, content_type: path)
    monkeypatch.setattr(services_media, "cleanup_artwork", failing_cleanup)
    monkeypatch.setattr(server.requests, "post", lambda *args, **kwargs: FakeResponse())
    user = server.User(user_id="user_123", email="mage@example.com", name="Mage", premium_manual=True)

    result = asyncio.run(server.generate_image(
        server.GenerateImageInput(type="spell", prompt="Un golem d'ombra", cleanup=True),
        user,
        segmind_key="test-key",
        db=fake_db,
    ))

    assert result["artwork_path"].endswith(".jpg")
    assert "pulizia" in result["cleanup_notice"].lower()
    assert fake_db.files.documents[0]["content_type"] == "image/jpeg"


def test_generated_artwork_skips_cleanup_unless_requested(monkeypatch):
    class FakeResponse:
        headers = {"content-type": "image/jpeg"}
        content = b"segmind-image-bytes"

        def raise_for_status(self):
            return None

    fake_db = FakeDatabase()
    cleanup_calls = []

    async def fake_cleanup(data, content_type):
        cleanup_calls.append((data, content_type))
        return b"cleaned-image-bytes", "image/png"

    monkeypatch.setattr(services_media, "put_object", lambda path, data, content_type: path)
    monkeypatch.setattr(services_media, "cleanup_artwork", fake_cleanup)
    monkeypatch.setattr(server.requests, "post", lambda *args, **kwargs: FakeResponse())
    user = server.User(user_id="user_123", email="mage@example.com", name="Mage", premium_manual=True)

    result = asyncio.run(server.generate_image(
        server.GenerateImageInput(type="spell", prompt="Una fenice di ossidiana"),
        user,
        segmind_key="test-key",
        db=fake_db,
    ))

    assert cleanup_calls == []
    assert result["artwork_path"].endswith(".jpg")
    assert fake_db.files.documents[0]["content_type"] == "image/jpeg"


def test_requested_artwork_cleanup_saves_original_when_unavailable(monkeypatch):
    class FakeResponse:
        headers = {"content-type": "image/jpeg"}
        content = b"segmind-image-bytes"

        def raise_for_status(self):
            return None

    fake_db = FakeDatabase()
    monkeypatch.setattr(services_media, "ARTWORK_CLEANUP_ENABLED", False)
    monkeypatch.setattr(services_media, "put_object", lambda path, data, content_type: path)
    monkeypatch.setattr(server.requests, "post", lambda *args, **kwargs: FakeResponse())
    user = server.User(user_id="user_123", email="mage@example.com", name="Mage", premium_manual=True)

    result = asyncio.run(server.generate_image(
        server.GenerateImageInput(type="spell", prompt="Un drago d'ombra", cleanup=True),
        user,
        segmind_key="test-key",
        db=fake_db,
    ))

    assert result["artwork_path"].endswith(".jpg")
    assert "pulizia" in result["cleanup_notice"].lower()
    assert fake_db.files.documents[0]["content_type"] == "image/jpeg"


def test_configured_admin_email_registers_as_admin_and_premium(monkeypatch):
    class FakeUsers:
        def __init__(self):
            self.documents = []

        async def find_one(self, query):
            return next((row for row in self.documents if row["email"] == query["email"]), None)

        async def insert_one(self, document):
            self.documents.append(document)

    fake_db = SimpleNamespace(users=FakeUsers())
    monkeypatch.setattr(core_auth_mod, "ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setattr(auth_router_mod, "create_jwt", lambda user_id: "test-token")

    result = asyncio.run(server.register(server.RegisterInput(
        email="admin@example.com",
        password="secure-test-password",
        name="Admin",
    ), db=fake_db))

    assert result["user"]["is_admin"] is True
    assert result["user"]["is_premium"] is True
    assert fake_db.users.documents[0]["is_admin"] is True
    assert fake_db.users.documents[0]["premium_manual"] is True


def test_configured_admin_email_is_promoted_after_google_login(monkeypatch):
    class FakeUsers:
        def __init__(self):
            self.documents = []

        async def find_one(self, query):
            return next((row for row in self.documents if row["email"] == query["email"]), None)

        async def insert_one(self, document):
            self.documents.append(document)

    external_user = SimpleNamespace(
        id="google-user-id",
        email="admin@example.com",
        user_metadata={"full_name": "Admin Google", "avatar_url": "https://example.com/avatar.png"},
    )
    fake_auth_client = SimpleNamespace(auth=SimpleNamespace(
        get_user=lambda access_token: SimpleNamespace(user=external_user)
    ))
    fake_db = SimpleNamespace(users=FakeUsers())
    monkeypatch.setattr(core_auth_mod, "ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setattr(auth_router_mod, "create_jwt", lambda user_id: "test-token")
    monkeypatch.setattr(auth_router_mod, "supabase_auth_client", lambda: fake_auth_client)

    result = asyncio.run(server.supabase_session(
        server.SupabaseSessionInput(access_token="google-token"),
        db=fake_db,
    ))

    assert result["user"]["is_admin"] is True
    assert result["user"]["is_premium"] is True
    assert fake_db.users.documents[0]["auth_provider"] == "google"


def test_google_start_uses_browser_compatible_implicit_flow(monkeypatch):
    monkeypatch.setattr(auth_router_mod, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(auth_router_mod, "SUPABASE_ANON_KEY", "anon-key")

    result = asyncio.run(server.google_start("https://app.example/oauth/callback"))
    parsed = urlparse(result["url"])
    query = parse_qs(parsed.query)

    assert parsed.geturl().startswith("https://project.supabase.co/auth/v1/authorize")
    assert query["provider"] == ["google"]
    assert query["redirect_to"] == ["https://app.example/oauth/callback"]
    assert "code_challenge" not in query


def test_ai_api_keys_ignore_accidental_surrounding_whitespace(monkeypatch):
    monkeypatch.setattr(core_providers_mod, "SEGMIND_API_KEY", "  segmind-key  ")
    monkeypatch.setattr(core_providers_mod, "OPENAI_API_KEY", "  openai-key  ")

    assert server.require_segmind() == "segmind-key"

    client = server.require_openai()
    assert client.api_key == "openai-key"

    monkeypatch.setattr(core_providers_mod, "GEMINI_API_KEY", "  gemini-key  ")
    assert server.require_gemini() == "gemini-key"


def test_get_db_override_supplies_fake_db_to_auth_and_route(monkeypatch):
    """Overriding get_db must reach both get_current_user (auth) and the route body."""
    import core.config as config_mod
    import core.auth as auth_mod
    import jwt as pyjwt
    from datetime import datetime, timezone, timedelta
    from fastapi.testclient import TestClient
    from core.db import get_db

    TEST_SECRET = "test-jwt-secret-di"
    monkeypatch.setattr(config_mod, "JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(auth_mod, "JWT_SECRET", TEST_SECRET)

    fake_user_doc = {
        "user_id": "di_test_user",
        "email": "di@example.com",
        "name": "DI Test User",
        "is_admin": False,
        "premium_manual": False,
        "premium_until": None,
    }
    db_access_log = []

    class FakeCursor:
        def __init__(self, docs):
            self._docs = list(docs)

        def sort(self, *args, **kwargs):
            return self

        async def to_list(self, limit):
            return self._docs[:limit] if limit else self._docs

    class FakeCollection:
        def __init__(self, name, initial_docs=()):
            self._name = name
            self._docs = list(initial_docs)

        async def find_one(self, query):
            db_access_log.append(("find_one", self._name))
            for doc in self._docs:
                if all(doc.get(k) == v for k, v in query.items() if not isinstance(v, dict)):
                    return doc
            return None

        def find(self, query=None):
            db_access_log.append(("find", self._name))
            return FakeCursor(self._docs)

    class FakeDB:
        def __init__(self):
            self.users = FakeCollection("users", [fake_user_doc])
            self.cards = FakeCollection("cards")

    fake_db = FakeDB()

    token = pyjwt.encode(
        {"user_id": fake_user_doc["user_id"], "exp": datetime.now(timezone.utc) + timedelta(days=1)},
        TEST_SECRET,
        algorithm="HS256",
    )
    if isinstance(token, bytes):
        token = token.decode()

    server.app.dependency_overrides[get_db] = lambda: fake_db
    try:
        with TestClient(server.app) as client:
            resp = client.get("/api/cards", cookies={"session_token": token})
    finally:
        server.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    queried = {entry[1] for entry in db_access_log}
    assert "users" in queried, f"Auth user lookup must use the injected fake DB; accessed: {queried}"
    assert "cards" in queried, f"Route body must use the injected fake DB; accessed: {queried}"
