import asyncio
from types import SimpleNamespace

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


def test_openai_content_response_is_mapped_to_card_fields(monkeypatch):
    class FakeCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content='{"name":"Nebbia runica","description":"Una nebbia protettiva.","story":"Nata tra le rovine.","attributes":{"livello":"2"}}'
                ))]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(server, "require_openai", lambda: fake_client)
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