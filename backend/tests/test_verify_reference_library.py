import pytest

import verify_reference_library as verifier


class FakeHttpResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def read(self):
        import json

        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeQuery:
    def __init__(self, rows=None, error=None, _offset=0):
        self.rows = rows or []
        self.error = error
        self._offset = _offset

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def range(self, start, _end):
        # Simulate pagination: first page returns rows, subsequent pages return empty.
        return FakeQuery(self.rows if start == 0 else [], self.error, _offset=start)

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
    player_handbook_types = {"feat", "race", "subrace", "spell"}
    rows = []
    for reference_type, name, normalized_name in (
        ("weapon", "Armi Di Adamantio", "armi di adamantio"),
        ("armor", "Armatura Fumigante", "armatura fumigante"),
        ("shield", "Scudo Dell'Espressione", "scudo dell espressione"),
        ("tool", "Strumenti Da Fabbro", "strumenti da fabbro"),
        ("magic_item", "Perla Dissetante", "perla dissetante"),
        ("feat", "Acechador", "acechador"),
        ("race", "Enano", "enano"),
        ("subrace", "Enano De Las Colinas", "enano de las colinas"),
        ("spell", "Bola De Fuego", "bola de fuego"),
    ):
        filename = (
            verifier.PLAYER_HANDBOOK_FILENAME
            if reference_type in player_handbook_types
            else "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf"
        )
        rows.append({
            "reference_type": reference_type,
            "name": name,
            "normalized_name": normalized_name,
            "review_flags": [],
            "source_refs": [{
                "filename": filename,
                "page": 150,
            }],
        })
    return rows


def test_verify_library_reports_required_equipment(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(verifier, "create_client", lambda *_args: FakeClient(FakeQuery(make_rows())))

    report = verifier.verify_library("owner-1")

    assert report["status"] == "ok"
    assert report["records_total"] == 9
    assert report["required_manual_records"][
        "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf"
    ] == 5
    assert report["required_manual_records"][verifier.PLAYER_HANDBOOK_FILENAME] == 4
    assert report["probes"]["magic_item"]["match"] == "Perla Dissetante"
    assert report["probes"]["feat"]["match"] == "Acechador"
    assert report["coverage_by_category"]["subrace"]["missing"] == 0


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


def test_verify_library_reports_dungeon_master_provenance_as_zero_when_absent(monkeypatch):
    """DMG absence is reported in required_manual_records but does not block PHB checks."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    rows = make_rows()
    # Clear DMG source_refs only; PHB records keep their refs so PHB check passes.
    for row in rows:
        if row["reference_type"] not in verifier.PLAYER_HANDBOOK_PROBE_TYPES:
            row["source_refs"] = []
    monkeypatch.setattr(verifier, "create_client", lambda *_args: FakeClient(FakeQuery(rows)))

    report = verifier.verify_library("owner-1")

    assert report["status"] == "ok"
    assert report["required_manual_records"][
        "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf"
    ] == 0


def test_verify_library_rejects_failed_character_option_translation(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    rows = make_rows()
    feat = next(row for row in rows if row["reference_type"] == "feat")
    feat.update({
        "translation_status": "failed",
        "review_status": "needs_review",
        "review_flags": ["traduzione_da_verificare"],
    })
    monkeypatch.setattr(verifier, "create_client", lambda *_args: FakeClient(FakeQuery(rows)))

    with pytest.raises(RuntimeError, match="controllo affidabile per feat"):
        verifier.verify_library("owner-1")


def test_verify_library_requires_player_handbook_for_character_option_probes(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    rows = make_rows()
    for row in rows:
        if row["reference_type"] in verifier.PLAYER_HANDBOOK_PROBE_TYPES:
            row["source_refs"] = [{
                "filename": "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf",
                "page": 150,
            }]
    monkeypatch.setattr(verifier, "create_client", lambda *_args: FakeClient(FakeQuery(rows)))

    with pytest.raises(RuntimeError, match="Manuale del Giocatore spagnolo"):
        verifier.verify_library("owner-1")


def test_verify_card_payload_uses_authenticated_owner_flow(monkeypatch):
    rows = make_rows()
    rows[0]["id"] = "reference-1"
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-with-at-least-32-bytes")
    seen_request = {}

    def fake_urlopen(request, timeout):
        seen_request["url"] = request.full_url
        seen_request["authorization"] = request.get_header("Authorization")
        seen_request["timeout"] = timeout
        return FakeHttpResponse({
            "reference_id": "reference-1",
            "reference_ids": ["reference-1"],
            "card_type": "weapon",
            "rule_source": {
                "source_kind": "reference",
                "source_id": "reference-1",
            },
        })

    monkeypatch.setattr(verifier.urllib.request, "urlopen", fake_urlopen)

    report = verifier.verify_card_payload("owner-1", rows, "http://api.example/api/")

    assert report == {
        "status": "ok",
        "reference_type": "weapon",
        "reference_link_retained": True,
        "provenance_retained": True,
        "card_persisted": False,
    }
    assert seen_request["url"] == "http://api.example/api/library/reference-1/apply"
    assert seen_request["authorization"].startswith("Bearer ")
    assert seen_request["timeout"] == 45


@pytest.mark.parametrize(
    ("payload_overrides", "error"),
    [
        ({"rule_source": {}}, "provenienza da riferimento"),
        (
            {"rule_source": {"source_kind": "reference", "source_id": "other-reference"}},
            "provenienza diversa",
        ),
        ({"card_type": "custom"}, "tipo della regola"),
    ],
)
def test_verify_card_payload_rejects_detached_provenance_or_wrong_type(
    monkeypatch,
    payload_overrides,
    error,
):
    rows = make_rows()
    rows[0]["id"] = "reference-1"
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-with-at-least-32-bytes")
    payload = {
        "reference_id": "reference-1",
        "reference_ids": ["reference-1"],
        "card_type": "weapon",
        "rule_source": {"source_kind": "reference", "source_id": "reference-1"},
    }
    payload.update(payload_overrides)
    monkeypatch.setattr(
        verifier.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeHttpResponse(payload),
    )

    with pytest.raises(RuntimeError, match=error):
        verifier.verify_card_payload("owner-1", rows, "http://api.example/api")