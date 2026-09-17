import asyncio

from scripts.purge_legacy_debris import (
    EXPECTED_DELETE_COUNT,
    EXPECTED_DELETE_IDS_MD5,
    EXPECTED_ISOLATE_COUNT,
    EXPECTED_ISOLATE_IDS_MD5,
    STRUCTURAL_TABLE_FLAG,
    STRUCTURAL_TABLE_TARGETS,
    _heading_family,
    _ids_md5,
    _isolate_structural_tables,
    _select_delete_targets,
)


def _row(record_id: str, name: str, reference_type: str = "other", *, status="verified", flags=None):
    return {
        "id": record_id,
        "name": name,
        "reference_type": reference_type,
        "review_status": status,
        "review_flags": list(flags or []),
    }


def test_heading_family_matches_confirmed_debris_but_not_real_name():
    assert _heading_family("C A P I T O L O 6 I B E S T I A R I O") == "capitolo"
    assert _heading_family("Appendice A: Stati") == "appendice"
    assert _heading_family("Passo 4. Grado Di Sfida Finale") == "passo"
    assert _heading_family("Tabell A Degli Oggetti Magici C") == "tabella"
    assert _heading_family("Statistiche Dei Mostri Per Grado Di Sfida") == "statistiche_dei_mostri"
    assert _heading_family("Passo Velato") is None
    assert _heading_family("Zuggtmoy") is None


def test_delete_selector_excludes_structural_tables():
    records = [
        _row("1", "Capitolo 2 I Bestiario", "monster"),
        _row("2", "Capitolo 7: Tesori"),
        _row("3", "Appendice A: Stati", "ability"),
        _row("4", "Passo 2. Statistiche Base", "monster"),
        _row("5", "Statistiche Dei Mostri Per Grado Di Sfida", "monster"),
        _row("6", "Tabella Degli Oggetti Magici A"),
        _row("7", "Zuggtmoy", "monster"),
    ]

    selected_ids = {row["id"] for row in _select_delete_targets(records)}
    assert selected_ids == {"1", "2", "3", "4", "5"}
    assert "6" not in selected_ids
    assert "7" not in selected_ids


def test_structural_table_snapshot_is_exactly_nine_and_sealed():
    rows = [_row(record_id, name) for record_id, name in STRUCTURAL_TABLE_TARGETS]
    assert len(rows) == EXPECTED_ISOLATE_COUNT == 9
    assert _ids_md5(rows) == EXPECTED_ISOLATE_IDS_MD5


def test_delete_snapshot_constants_are_explicitly_94():
    assert EXPECTED_DELETE_COUNT == 94
    assert EXPECTED_DELETE_IDS_MD5 == "203cb5e825490842f5ad8354ff077156"


def test_isolation_preserves_existing_flags_and_never_deletes():
    class Result:
        def __init__(self, count):
            self.matched_count = count

    class FakeCollection:
        def __init__(self, row):
            self.row = row
            self.delete_called = False

        async def find_one(self, query):
            if query.get("id") == self.row["id"]:
                return dict(self.row)
            return None

        async def update_one(self, query, update):
            assert query == {"id": self.row["id"], "review_status": "verified"}
            self.row.update(update["$set"])
            return Result(1)

        async def delete_one(self, *_args, **_kwargs):
            self.delete_called = True
            raise AssertionError("structural table must never be deleted")

    original = _row(
        "table-1",
        "Tabella Degli Oggetti Magici A",
        flags=["ocr_da_verificare", "sezione_potenzialmente_continua"],
    )
    collection = FakeCollection(original)

    changed = asyncio.run(_isolate_structural_tables(collection, [dict(original)]))

    assert changed == 1
    assert collection.delete_called is False
    assert collection.row["review_status"] == "needs_review"
    assert set(collection.row["review_flags"]) == {
        "ocr_da_verificare",
        "sezione_potenzialmente_continua",
        STRUCTURAL_TABLE_FLAG,
    }


def test_isolation_is_idempotent_after_safe_partial_retry():
    class FakeCollection:
        def __init__(self, row):
            self.row = row

        async def find_one(self, query):
            return dict(self.row) if query.get("id") == self.row["id"] else None

        async def update_one(self, *_args, **_kwargs):
            raise AssertionError("already isolated row must not be updated again")

    row = _row(
        "table-1",
        "Tabella Degli Oggetti Magici A",
        status="needs_review",
        flags=["ocr_da_verificare", STRUCTURAL_TABLE_FLAG],
    )

    changed = asyncio.run(_isolate_structural_tables(FakeCollection(row), [row]))
    assert changed == 0
