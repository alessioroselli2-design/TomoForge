"""Regression: the library search must not silently lose recent monsters."""

import asyncio
from types import SimpleNamespace

from reference_library import reference_to_card_payload, search_reference_records
from services.library import private_reference_records


class LimitedCursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, field, direction):
        assert field == "id"
        assert direction == 1
        self.rows = sorted(self.rows, key=lambda row: row[field])
        return self

    async def to_list(self, limit, offset=0):
        # Simulate PostgREST server max-rows and enforce bounded requests.
        assert 0 < limit <= 500
        return self.rows[offset : offset + min(limit, 500)]


class LimitedCollection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def find(self, query):
        self.calls += 1
        data = [row for row in self.rows if row["user_id"] == query["user_id"]]
        types = query.get("reference_type")
        if types is not None:
            data = [row for row in data if row["reference_type"] in types["$in"]]
        return LimitedCursor(data)


def test_owner_collection_over_eight_thousand_is_paginated():
    rows = [
        {
            "id": f"r-{i:05d}",
            "user_id": "owner",
            "name": f"Other {i}",
            "reference_type": "other",
        }
        for i in range(7144)
    ]
    rows.extend(
        {
            "id": f"z-{i:05d}",
            "user_id": "owner",
            "name": ("Creeper" if i == 1498 else "Abyssal Wretch" if i == 1499 else f"Monster {i}"),
            "reference_type": "monster",
            "review_status": "verified",
            "normalized_name": ("creeper" if i == 1498 else "abyssal wretch" if i == 1499 else f"monster {i}"),
        }
        for i in range(1500)
    )
    rows.append({"id": "outsider", "user_id": "someone-else", "reference_type": "monster", "name": "Foreign"})
    collection = LimitedCollection(rows)
    db = SimpleNamespace(private_reference_records=collection)

    complete = asyncio.run(private_reference_records("owner", db=db))
    assert len(complete) == 8644
    assert collection.calls > 16
    assert complete[-1]["name"] == "Abyssal Wretch"
    assert all(row["user_id"] == "owner" for row in complete)

    collection.calls = 0
    monsters = asyncio.run(private_reference_records("owner", db=db, reference_types={"monster"}))
    assert len(monsters) == 1500
    assert collection.calls == 4
    assert search_reference_records(monsters, "Creeper", limit=5)[0]["name"] == "Creeper"
    assert search_reference_records(monsters, "Abyssal Wretch", limit=5)[0]["name"] == "Abyssal Wretch"


def test_monster_card_payload_flattens_six_abilities_without_touching_source():
    scores = {"for": 10, "des": 11, "cos": 14, "int": 6, "sag": 8, "car": 3}
    record = {
        "id": "creeper-id",
        "reference_type": "monster",
        "name": "Creeper",
        "review_status": "verified",
        "attributes": {
            "classe_armatura": "12 (natural armor)",
            "punti_ferita": "19 (3d8 + 6)",
            "velocita": "30 ft.",
            "grado_sfida": "1/2",
            "caratteristiche": scores,
        },
    }
    card = reference_to_card_payload(record)
    assert card["card_type"] == "monster"
    assert all(card["attributes"][key] == val for key, val in scores.items())
    assert card["attributes"]["classe_armatura"] == "12 (natural armor)"
    assert card["attributes"]["punti_ferita"] == "19 (3d8 + 6)"
    assert "caratteristiche" not in card["attributes"]
    assert record["attributes"]["caratteristiche"] == scores
