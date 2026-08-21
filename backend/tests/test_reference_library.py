import asyncio
from types import SimpleNamespace

import server
from reference_library import (
    merge_reference_records,
    normalize_reference_name,
    parse_reference_page,
    reference_to_card_payload,
    search_reference_records,
)


def make_reference(name, reference_type="feat", **changes):
    record = {
        "id": f"ref-{normalize_reference_name(name).replace(' ', '-')}",
        "user_id": "owner-1",
        "reference_type": reference_type,
        "name": name,
        "normalized_name": normalize_reference_name(name),
        "description": "Un contenuto regolamentare tratto dal manuale privato.",
        "full_text": "Un contenuto regolamentare tratto dal manuale privato con dettagli verificabili.",
        "attributes": {"prerequisito": "Forza 13"} if reference_type == "feat" else {},
        "tags": [],
        "source_refs": [{"filename": "Manuale.pdf", "page": 42}],
        "review_flags": [],
        "review_status": "pending",
        "review_notes": "",
    }
    record.update(changes)
    return record


def test_reference_parser_keeps_heading_provenance_and_marks_open_section():
    page = """MAESTRO DELLA BATTAGLIA
Quando scegli questo archetipo al 3° livello, apprendi manovre che alimentano
la tua superiorità in combattimento. Puoi usare i dadi di superiorità per
influenzare un attacco, una prova di caratteristica o un tiro salvezza.
"""
    records = parse_reference_page(page, "Xanathar.pdf", 48)

    assert len(records) == 1
    assert records[0]["reference_type"] == "subclass"
    assert records[0]["source_refs"] == [{"filename": "Xanathar.pdf", "page": 48}]
    assert records[0]["review_flags"] == ["sezione_potenzialmente_continua"]


def test_reference_parser_detects_base_class_for_class_picker():
    page = """GUERRIERO
Un guerriero è un maestro del combattimento marziale. Il dado vita è d10.
Le sue abilità primarie sono Forza e Destrezza e apprende numerosi privilegi.
"""
    records = parse_reference_page(page, "Manuale del giocatore.pdf", 45)

    assert len(records) == 1
    assert records[0]["reference_type"] == "class"


def test_reference_extractor_uses_ocr_callback_for_unreadable_page(tmp_path):
    import fitz
    from reference_library import extract_reference_records

    pdf_path = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    report = extract_reference_records(
        pdf_path,
        ocr_page=lambda page, page_number: """TALENTO DELLA GUERRA
Prerequisito: Forza 13. Questo talento migliora il combattimento e offre un beneficio verificabile.
""",
    )

    assert report.pages_read == 1
    assert report.pages_needing_ocr == []
    assert report.records[0]["reference_type"] == "feat"


def test_reference_extractor_flags_only_empty_ocr_page_without_aborting_batch(tmp_path):
    import fitz
    from reference_library import extract_reference_records

    pdf_path = tmp_path / "scan-empty-ocr.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    report = extract_reference_records(pdf_path, ocr_page=lambda page, page_number: "")

    assert report.pages_read == 0
    assert report.pages_needing_ocr == [1]
    assert report.records == []


def test_reference_extractor_continues_after_one_failed_ocr_page(tmp_path):
    import fitz
    from reference_library import extract_reference_records

    pdf_path = tmp_path / "scan-partial-ocr.pdf"
    document = fitz.open()
    document.new_page()
    document.new_page()
    document.save(pdf_path)
    document.close()

    report = extract_reference_records(
        pdf_path,
        ocr_page=lambda page, page_number: "" if page_number == 1 else """TALENTO DELLA GUERRA
Prerequisito: Forza 13. Questo talento migliora il combattimento e offre un beneficio verificabile.
""",
    )

    assert report.pages_read == 1
    assert report.pages_needing_ocr == [1]
    assert report.records[0]["reference_type"] == "feat"


class _OcrPage:
    class _Pixmap:
        def tobytes(self, format_name):
            return b"png"

    def get_pixmap(self, **kwargs):
        return self._Pixmap()


class _OcrResponse:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


def test_gemini_ocr_returns_empty_for_http_transport_and_malformed_responses(monkeypatch):
    from requests import HTTPError, Timeout

    http_error = HTTPError("rate limited")
    http_error.response = SimpleNamespace(status_code=429)
    responses = [
        _OcrResponse(error=http_error),
        Timeout("connection timed out"),
        _OcrResponse(payload=[]),
        _OcrResponse(payload={"candidates": [None]}),
        _OcrResponse(payload={"candidates": [{"content": None}]}),
    ]

    def fake_post(*args, **kwargs):
        next_response = responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response

    monkeypatch.setattr(server.requests, "post", fake_post)
    monkeypatch.setattr(server, "GEMINI_API_KEY", "test-key")

    for _ in range(5):
        assert server.gemini_ocr_manual_page(_OcrPage(), 7) == ""


def test_equipment_table_rows_create_structured_weapon_armor_and_item_records():
    page = """ARMI
Spada lunga 15 mo 1d8 taglienti 1,5 kg Versatile (1d10)
Mazza 5 mo 1d6 contundenti 2 kg
ARMATURE
Armatura di cuoio 10 mo CA 11 5 kg
Scudo 10 mo CA +2 3 kg
EQUIPAGGIAMENTO
Zaino 2 mo 2,5 kg Contiene fino a 15 kg di equipaggiamento.
"""
    records = parse_reference_page(page, "Manuale del giocatore.pdf", 145)
    by_name = {record["name"]: record for record in records}

    assert by_name["Spada Lunga"]["reference_type"] == "weapon"
    assert by_name["Spada Lunga"]["attributes"]["danno"] == "1d8"
    assert by_name["Armatura Di Cuoio"]["reference_type"] == "armor"
    assert by_name["Armatura Di Cuoio"]["attributes"]["classe_armatura"] == "11"
    assert by_name["Scudo"]["reference_type"] == "shield"
    assert by_name["Zaino"]["reference_type"] == "equipment"
    assert by_name["Zaino"]["attributes"]["costo"] == "2 mo"
    assert "riga_tabella_da_verificare" in by_name["Zaino"]["review_flags"]


def test_equipment_card_payloads_map_to_their_dedicated_card_types():
    weapon = reference_to_card_payload(make_reference(
        "Spada lunga",
        reference_type="weapon",
        attributes={"danno": "1d8", "tipo_danno": "taglienti", "categoria": "Arma"},
    ))
    armor = reference_to_card_payload(make_reference(
        "Armatura di cuoio",
        reference_type="armor",
        attributes={"classe_armatura": "11", "categoria": "Armatura"},
    ))
    item = reference_to_card_payload(make_reference(
        "Zaino",
        reference_type="equipment",
        attributes={"categoria": "Equipaggiamento", "peso": "2,5 kg"},
    ))

    assert weapon["card_type"] == "weapon"
    assert armor["card_type"] == "armor"
    assert item["card_type"] == "item"


def test_magic_items_tools_and_vehicles_receive_equipment_categories():
    page = """MANTELLO DI PROTEZIONE
Oggetto meraviglioso, raro (richiede sintonia). Finché lo indossi, ottieni un bonus
di +1 alla CA e ai tiri salvezza. Questo oggetto conserva una descrizione verificabile.
STRUMENTI
Strumenti da scasso 25 mo 0,5 kg
VEICOLI
Carro 100 mo 200 kg
"""
    records = parse_reference_page(page, "Manuale.pdf", 201)
    by_name = {record["name"]: record for record in records}

    assert by_name["Mantello Di Protezione"]["reference_type"] == "magic_item"
    assert by_name["Mantello Di Protezione"]["attributes"]["rarita"] == "raro"
    assert by_name["Mantello Di Protezione"]["attributes"]["sintonia"] == "Richiede sintonia"
    assert by_name["Strumenti Da Scasso"]["reference_type"] == "tool"
    assert by_name["Carro"]["reference_type"] == "vehicle"


def test_ammunition_mount_trade_goods_and_services_remain_distinct_items():
    page = """MUNIZIONI
Frecce (20) 1 mo 0,5 kg
CAVALCATURE
Cavallo da guerra 400 mo 200 kg
MERCI COMMERCIALI
Ferro (1 kg) 1 ma 1 kg
SERVIZI
Passaggio su nave 1 mo 0 kg
"""
    records = parse_reference_page(page, "Manuale.pdf", 148)
    by_name = {record["name"]: record for record in records}

    assert by_name["Frecce (20)"]["reference_type"] == "ammunition"
    assert by_name["Cavallo Da Guerra"]["reference_type"] == "mount"
    assert by_name["Ferro (1 Kg)"]["reference_type"] == "trade_good"
    assert by_name["Passaggio Su Nave"]["reference_type"] == "service"


def test_reference_merge_deduplicates_but_preserves_sources_and_review_flags():
    first = make_reference("Tiratore Scelto")
    second = make_reference(
        "Tiratore scelto",
        source_refs=[{"filename": "Xanathar.pdf", "page": 75}],
        review_flags=["ocr_da_verificare"],
    )
    merged = merge_reference_records([first, second])

    assert len(merged) == 1
    assert len(merged[0]["source_refs"]) == 2
    assert merged[0]["review_flags"] == ["ocr_da_verificare"]


def test_reference_search_is_accent_case_and_typo_tolerant():
    records = [make_reference("Maestro delle Armi"), make_reference("Fortunato")]
    matches = search_reference_records(records, "màestr armi")

    assert [record["name"] for record in matches] == ["Maestro delle Armi"]


def test_reference_card_payload_maps_feat_without_inventing_rules():
    payload = reference_to_card_payload(make_reference("Tiratore Scelto"))

    assert payload["source"] == "biblioteca_privata"
    assert payload["card_type"] == "feat"
    assert payload["attributes"]["prerequisito"] == "Forza 13"


class MemoryReferences:
    def __init__(self, rows):
        self.rows = rows

    async def find_one(self, query):
        return next((row.copy() for row in self.rows if all(row.get(key) == value for key, value in query.items())), None)

    def find(self, query):
        rows = [row.copy() for row in self.rows if all(row.get(key) == value for key, value in query.items())]
        return SimpleNamespace(to_list=lambda limit: asyncio.sleep(0, result=rows[:limit]))


class MutableMemoryReferences(MemoryReferences):
    async def insert_one(self, document):
        self.rows.append(document.copy())

    async def update_one(self, query, update):
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                row.update(update.get("$set", update))


def test_apply_reference_endpoint_cannot_read_another_users_record(monkeypatch):
    record = make_reference("Tiratore Scelto", user_id="owner-1")
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=MemoryReferences([record])))
    other_user = server.User(user_id="owner-2", email="other@example.com", name="Other")

    try:
        asyncio.run(server.apply_private_reference(record["id"], other_user))
        assert False, "Expected a not-found response for another user's record"
    except server.HTTPException as error:
        assert error.status_code == 404


def test_generate_content_prefers_matching_private_reference_before_gemini(monkeypatch):
    record = make_reference("Tiratore Scelto")
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=MemoryReferences([record])))
    monkeypatch.setattr(server, "GEMINI_API_KEY", None)
    user = server.User(user_id="owner-1", email="ranger@example.com", name="Ranger", premium_manual=True)

    payload = asyncio.run(server.generate_content(
        server.GenerateContentInput(type="feat", prompt="tirator scelto"),
        user,
    ))

    assert payload["source"] == "biblioteca_privata"
    assert payload["name"] == "Tiratore Scelto"


def test_same_source_import_uses_distinct_ids_for_distinct_owners(monkeypatch, tmp_path):
    source = tmp_path / "Manuale.pdf"
    source.write_bytes(b"not-read")
    record = make_reference("Tiratore Scelto")
    collection = MutableMemoryReferences([])
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {"Manuale.pdf": source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args, **kwargs: SimpleNamespace(records=[record], pages_read=1, pages_needing_ocr=[]),
    )
    body = server.ReferenceImportInput(filenames=["Manuale.pdf"])

    asyncio.run(server.import_private_reference_manuals("owner-1", body))
    asyncio.run(server.import_private_reference_manuals("owner-2", body))

    assert len(collection.rows) == 2
    assert collection.rows[0]["id"] != collection.rows[1]["id"]


def test_ocr_import_requires_server_side_confirmation_and_one_manual(monkeypatch, tmp_path):
    first = tmp_path / "Primo.pdf"
    second = tmp_path / "Secondo.pdf"
    first.write_bytes(b"not-read")
    second.write_bytes(b"not-read")
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {"Primo.pdf": first, "Secondo.pdf": second})

    try:
        asyncio.run(server.import_private_reference_manuals(
            "owner-1",
            server.ReferenceImportInput(
                filenames=["Primo.pdf"],
                use_ai_ocr=True,
                start_page=5,
                end_page=8,
                external_processing_confirmed=False,
            ),
        ))
        assert False, "Expected OCR confirmation failure"
    except server.HTTPException as error:
        assert error.status_code == 400

    try:
        asyncio.run(server.import_private_reference_manuals(
            "owner-1",
            server.ReferenceImportInput(
                filenames=["Primo.pdf", "Secondo.pdf"],
                use_ai_ocr=True,
                start_page=5,
                end_page=8,
                external_processing_confirmed=True,
            ),
        ))
        assert False, "Expected one-manual OCR failure"
    except server.HTTPException as error:
        assert error.status_code == 400