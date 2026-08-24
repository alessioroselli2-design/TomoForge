import asyncio
from types import SimpleNamespace

import server
from spell_library import (
    merge_spell_records,
    normalize_spell_name,
    parse_spell_page,
    search_spell_records,
    spell_to_card_payload,
)


def make_spell(name, **changes):
    spell = {
        "id": f"spell-{normalize_spell_name(name).replace(' ', '-')}",
        "user_id": "owner-1",
        "name": name,
        "normalized_name": normalize_spell_name(name),
        "level": "3",
        "school": "Invocazione",
        "casting_time": "1 azione",
        "range": "45 metri",
        "components": "V, S, M",
        "duration": "Istantanea",
        "description": "Un'esplosione di fuoco arcano.",
        "classes": ["Mago"],
        "source_refs": [{"filename": "Mago.pdf", "page": 12}],
        "review_flags": [],
    }
    spell.update(changes)
    return spell


def test_parser_accepts_italian_ranger_headers_and_extracts_fields():
    page = """TEMPO DI LANCIO
1 azione
GITTATA
18 metri
COMPONENTI
V, S
DURATA
Concentrazione, fino a 1 minuto
COLPO DELLO ZEFIRO
Il vento circonda l'incantatore e gli offre una rapida apertura.
Ranger (XGE)
1° livello Trasmutazione
"""
    records = parse_spell_page(page, "Ranger.pdf", 2, "Ranger")

    assert len(records) == 1
    record = records[0]
    assert record["name"] == "Colpo Dello Zefiro"
    assert record["casting_time"] == "1 azione"
    assert record["range"] == "18 metri"
    assert record["level"] == "1"
    assert record["school"] == "Trasmutazione"
    assert record["classes"] == ["Ranger"]


def test_merge_deduplicates_name_and_retains_classes_and_sources():
    first = make_spell("Palla di Fuoco")
    second = make_spell(
        "Palla di fuoco",
        classes=["Stregone"],
        source_refs=[{"filename": "Stregone.pdf", "page": 10}],
    )

    merged = merge_spell_records([first, second])

    assert len(merged) == 1
    assert merged[0]["classes"] == ["Mago", "Stregone"]
    assert len(merged[0]["source_refs"]) == 2


def test_search_is_case_accent_and_typo_tolerant():
    records = [
        make_spell("Palla di Fuoco"),
        make_spell("Passo Velato"),
    ]

    result = search_spell_records(records, "pàlla di fuoc")

    assert [spell["name"] for spell in result] == ["Palla di Fuoco"]


def test_spell_payload_preserves_rules_and_compacts_card_copy():
    spell = make_spell(
        "Palla di Fuoco",
        duration="Istantanea",
        description="Parola " * 200,
        classes=["Mago", "Stregone"],
    )
    payload = spell_to_card_payload(spell)

    assert payload["source"] == "grimorio"
    assert payload["attributes"]["livello"] == "3"
    assert payload["attributes"]["azione"] == "1 azione"
    assert payload["attributes"]["concentrazione"] == "No"
    assert len(payload["description"]) <= 620
    assert "Mago, Stregone" in payload["story"]
    assert payload["rule_source"] == {
        "source_kind": "spell",
        "source_id": spell["id"],
        "name": "Palla di Fuoco",
        "reference_type": "spell",
        "source_refs": spell["source_refs"],
    }


class MemorySpells:
    def __init__(self, rows):
        self.rows = rows

    async def find_one(self, query):
        return next(
            (
                row.copy()
                for row in self.rows
                if all(row.get(key) == value for key, value in query.items())
            ),
            None,
        )

    def find(self, query):
        rows = [
            row.copy()
            for row in self.rows
            if all(row.get(key) == value for key, value in query.items())
        ]
        return SimpleNamespace(to_list=lambda limit: asyncio.sleep(0, result=rows[:limit]))


def test_apply_endpoint_cannot_read_another_users_spell(monkeypatch):
    spell = make_spell("Palla di Fuoco", user_id="owner-1")
    fake_db = SimpleNamespace(private_spells=MemorySpells([spell]))
    other_user = server.User(user_id="owner-2", email="other@example.com", name="Other")

    try:
        asyncio.run(server.apply_private_spell(spell["id"], other_user, db=fake_db))
        assert False, "Expected a not-found response for another user's spell"
    except server.HTTPException as error:
        assert error.status_code == 404


def test_generate_content_prefers_matching_private_spell_before_gemini(monkeypatch):
    spell = make_spell("Palla di Fuoco")
    _test_db = SimpleNamespace(private_spells=MemorySpells([spell]))
    user = server.User(user_id="owner-1", email="mage@example.com", name="Mage", premium_manual=True)

    payload = asyncio.run(server.generate_content(
        server.GenerateContentInput(type="spell", prompt="palla di fuoc"),
        user,
        gemini_key=None,
        db=_test_db,
    ))

    assert payload["source"] == "grimorio"
    assert payload["name"] == "Palla di Fuoco"


def test_generate_content_falls_back_to_gemini_for_missing_spell(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{
                "text": '{"name":"Nebbia runica","description":"Una nebbia.","story":"Antica.","attributes":{"livello":"2"}}'
            }]}}]}

    _test_db = SimpleNamespace(private_spells=MemorySpells([]))
    monkeypatch.setattr(server.requests, "post", lambda *args, **kwargs: FakeResponse())
    user = server.User(user_id="owner-1", email="mage@example.com", name="Mage", premium_manual=True)

    payload = asyncio.run(server.generate_content(
        server.GenerateContentInput(type="spell", prompt="Nebbia inesistente"),
        user,
        gemini_key="test-key",
        db=_test_db,
    ))

    assert payload["name"] == "Nebbia runica"
    assert payload["source"] == "ai_generated"
    assert payload["source_status"] == "unavailable"
