import asyncio
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import server


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
    monkeypatch.setattr(server, "db", fake_db)
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
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "put_object", lambda path, data, content_type: path)

    saved_path = asyncio.run(server.save_file(
        "uploads/user_123/card.png", b"image-bytes", "image/png", "user_123", "card.png"
    ))

    assert saved_path == "uploads/user_123/card.png"
    assert fake_db.files.documents[0]["user_id"] == "user_123"
    assert fake_db.files.documents[0]["content_type"] == "image/png"


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

    monkeypatch.setattr(server, "GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(server.requests, "post", fake_post)
    user = server.User(user_id="user_123", email="mage@example.com", name="Mage", premium_manual=True)

    result = asyncio.run(server.generate_content(
        server.GenerateContentInput(type="spell", prompt="Una nebbia protettiva"),
        user,
    ))

    assert result == {
        "name": "Nebbia runica",
        "description": "Una nebbia protettiva.",
        "story": "Nata tra le rovine.",
        "attributes": {"livello": "2"},
    }
    assert request_data["url"].endswith("/models/gemini-2.5-flash:generateContent")
    assert request_data["params"] == {"key": "test-gemini-key"}


def test_segmind_image_response_is_saved_as_card_artwork(monkeypatch):
    class FakeResponse:
        headers = {"content-type": "image/jpeg"}
        content = b"segmind-image-bytes"

        def raise_for_status(self):
            return None

    fake_db = FakeDatabase()
    request_data = {}

    def fake_post(url, **kwargs):
        request_data["url"] = url
        request_data.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "put_object", lambda path, data, content_type: path)
    monkeypatch.setattr(server, "require_segmind", lambda: "test-key")
    monkeypatch.setattr(server.requests, "post", fake_post)
    user = server.User(user_id="user_123", email="mage@example.com", name="Mage", premium_manual=True)

    result = asyncio.run(server.generate_image(
        server.GenerateImageInput(type="spell", prompt="Una fenice di ossidiana"),
        user,
    ))

    assert request_data["url"].endswith("/fast-flux-schnell")
    assert request_data["headers"]["x-api-key"] == "test-key"
    assert request_data["json"]["aspect_ratio"] == "2:3"
    assert "no text" in request_data["json"]["prompt"]
    assert result["artwork_path"].endswith(".jpg")
    assert fake_db.files.documents[0]["content_type"] == "image/jpeg"
    assert fake_db.files.documents[0]["original_filename"] == "segmind-generated.jpg"


def test_configured_admin_email_registers_as_admin_and_premium(monkeypatch):
    class FakeUsers:
        def __init__(self):
            self.documents = []

        async def find_one(self, query):
            return next((row for row in self.documents if row["email"] == query["email"]), None)

        async def insert_one(self, document):
            self.documents.append(document)

    fake_db = SimpleNamespace(users=FakeUsers())
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setattr(server, "create_jwt", lambda user_id: "test-token")

    result = asyncio.run(server.register(server.RegisterInput(
        email="admin@example.com",
        password="secure-test-password",
        name="Admin",
    )))

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
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setattr(server, "create_jwt", lambda user_id: "test-token")
    monkeypatch.setattr(server, "supabase_auth_client", lambda: fake_auth_client)

    result = asyncio.run(server.supabase_session(server.SupabaseSessionInput(access_token="google-token")))

    assert result["user"]["is_admin"] is True
    assert result["user"]["is_premium"] is True
    assert fake_db.users.documents[0]["auth_provider"] == "google"


def test_google_start_uses_browser_compatible_implicit_flow(monkeypatch):
    monkeypatch.setattr(server, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(server, "SUPABASE_ANON_KEY", "anon-key")

    result = asyncio.run(server.google_start("https://app.example/oauth/callback"))
    parsed = urlparse(result["url"])
    query = parse_qs(parsed.query)

    assert parsed.geturl().startswith("https://project.supabase.co/auth/v1/authorize")
    assert query["provider"] == ["google"]
    assert query["redirect_to"] == ["https://app.example/oauth/callback"]
    assert "code_challenge" not in query


def test_ai_api_keys_ignore_accidental_surrounding_whitespace(monkeypatch):
    monkeypatch.setattr(server, "SEGMIND_API_KEY", "  segmind-key  ")
    monkeypatch.setattr(server, "OPENAI_API_KEY", "  openai-key  ")

    assert server.require_segmind() == "segmind-key"

    client = server.require_openai()
    assert client.api_key == "openai-key"

    monkeypatch.setattr(server, "GEMINI_API_KEY", "  gemini-key  ")
    assert server.require_gemini() == "gemini-key"