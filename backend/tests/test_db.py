import asyncio
from pathlib import Path
from types import SimpleNamespace

from core.db import SupabaseCollection


class FakeStatement:
    def __init__(self):
        self.selected = None

    def eq(self, _field, _value):
        return self

    def select(self, fields):
        self.selected = fields
        return self

    def execute(self):
        return SimpleNamespace(data=[{self.selected: "updated"}])


class FakeClient:
    def __init__(self):
        self.statement = FakeStatement()

    def table(self, _name):
        return self

    def update(self, _changes):
        return self.statement


class FakeDatabase:
    def __init__(self):
        self.client = FakeClient()


def test_users_update_uses_user_id_projection():
    database = FakeDatabase()
    collection = SupabaseCollection(database, "users")

    result = asyncio.run(collection.update_one({"user_id": "user-1"}, {"$set": {"name": "Google User"}}))

    assert result.matched_count == 1
    assert database.client.statement.selected == "user_id"


def test_cards_schema_keeps_all_provenance_columns():
    schema = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text()

    for column in ("reference_ids", "spell_ids", "rule_sources", "source_refs", "reference_snapshots"):
        assert f"{column} jsonb not null default '[]'::jsonb" in schema
