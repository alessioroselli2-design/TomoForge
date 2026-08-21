import pytest

import verify_reference_library as verifier


class FakeQuery:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        if self.error:
            raise self.error
        return type("Response", (), {"data": self.rows})()


class FakeClient:
    def __init__(self, query):
        self.query = query

    def table(self, _name):
        return self.query


def make_rows():
    return [
        {
            "reference_type": reference_type,
            "name": name,
            "normalized_name": normalized_name,
            "review_flags": [],
            "source_refs": [{
                "filename": "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf",
                "page": 150,
            }],
        }
        for reference_type, name, normalized_name in (
            ("weapon", "Armi Di Adamantio", "armi di adamantio"),
            ("armor", "Armatura Fumigante", "armatura fumigante"),
            ("shield", "Scudo Dell'Espressione", "scudo dell espressione"),
            ("tool", "Strumenti Da Fabbro", "strumenti da fabbro"),
            ("magic_item", "Perla Dissetante", "perla dissetante"),
        )
    ]


def test_verify_library_reports_required_equipment(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(verifier, "create_client", lambda *_args: FakeClient(FakeQuery(make_rows())))

    report = verifier.verify_library("owner-1")

    assert report["status"] == "ok"
    assert report["records_total"] == 5
    assert report["required_manual_records"][
        "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf"
    ] == 5
    assert report["probes"]["magic_item"]["match"] == "Perla Dissetante"


def test_verify_library_fails_clearly_when_schema_is_missing(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(
        verifier,
        "create_client",
        lambda *_args: FakeClient(FakeQuery(error=RuntimeError("PGRST205"))),
    )

    with pytest.raises(RuntimeError, match="private_reference_records"):
        verifier.verify_library("owner-1")


def test_verify_library_requires_dungeon_master_provenance(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    rows = make_rows()
    for row in rows:
        row["source_refs"] = []
    monkeypatch.setattr(verifier, "create_client", lambda *_args: FakeClient(FakeQuery(rows)))

    with pytest.raises(RuntimeError, match="Manuale del Dungeon Master"):
        verifier.verify_library("owner-1")