import asyncio
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import server
from reference_library import (
    merge_reference_records,
    normalize_reference_name,
    parse_reference_page,
    reference_is_trusted,
    reference_review_state,
    reference_snapshot,
    reference_snapshot_changed,
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


def test_reference_parser_extracts_structured_class_and_race_creation_fields():
    class_record = parse_reference_page(
        """GUERRIERO
Il guerriero è un maestro del combattimento. Dado Vita: d10. Abilità primaria:
Forza o Destrezza. Tiri Salvezza: Forza, Costituzione. Competenze: armature,
scudi e armi semplici. Questa descrizione contiene abbastanza dettagli verificabili.
""",
        "Manuale del giocatore.pdf",
        45,
    )[0]
    race_record = parse_reference_page(
        """ELFO
Gli elfi possiedono sensi acuti e un retaggio fatato. Velocità: 9 metri.
Taglia: Media. Linguaggi: Comune, Elfico. Il tuo punteggio di Destrezza aumenta
di 2 e questo tratto resta documentato nella fonte del manuale.
""",
        "Manuale del giocatore.pdf",
        22,
    )[0]

    assert class_record["attributes"]["dado_vita"] == "d10"
    assert class_record["attributes"]["tiri_salvezza"] == "Forza, Costituzione"
    assert "armature" in class_record["attributes"]["competenze"]
    assert race_record["attributes"]["velocita"] == "9 metri"
    assert race_record["attributes"]["linguaggi"] == "Comune, Elfico"


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
    assert "ocr_da_verificare" in report.records[0]["review_flags"]
    assert not reference_is_trusted(report.records[0])


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


def test_reference_extractor_can_require_ocr_for_broken_text_layer(tmp_path):
    import fitz
    from reference_library import extract_reference_records

    pdf_path = tmp_path / "broken-text.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "TALENTO DELLA GUERRA " * 8)
    document.save(pdf_path)
    document.close()

    report = extract_reference_records(pdf_path, force_ocr=True)

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


def test_subclass_and_class_feature_keep_dedicated_printable_card_types():
    subclass = reference_to_card_payload(make_reference("Maestro della battaglia", reference_type="subclass"))
    feature = reference_to_card_payload(make_reference(
        "Superiorità in combattimento",
        reference_type="class_feature",
        attributes={"livello": "3", "benefici": ["Manovre"]},
    ))

    assert subclass["card_type"] == "subclass"
    assert feature["card_type"] == "feature"
    assert feature["attributes"]["benefici"] == ["Manovre"]


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


def test_translated_or_flagged_reference_requires_human_verification_before_use():
    translated = make_reference(
        "Palla di Fuoco",
        reference_type="spell",
        source_language="es",
        translation_status="translated",
    )
    ocr_flagged = make_reference(
        "Colpo Preciso",
        reference_type="class_feature",
        review_flags=["ocr_da_verificare"],
        review_status="needs_review",
    )

    assert reference_review_state(translated) == "review"
    assert reference_review_state(ocr_flagged) == "review"
    assert not reference_is_trusted(translated)
    assert not reference_is_trusted(ocr_flagged)

    translated["review_status"] = "verified"
    ocr_flagged["review_status"] = "verified"
    assert reference_is_trusted(translated)
    assert reference_is_trusted(ocr_flagged)


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
        count = 0
        for row in self.rows:
            if server.MemoryCollection.matches(row, query):
                row.update(update.get("$set", update))
                count += 1
        return server.UpdateResult(count)


def test_character_references_derive_source_refs_and_create_only_selected_rule_cards(monkeypatch):
    record = make_reference("Tiratore scelto")
    references = server.MemoryCollection()
    references.rows.append(record)
    cards = server.MemoryCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=references))
    user = server.User(user_id="owner-1", email="ranger@example.com", name="Ranger")

    character = asyncio.run(server.create_card(server.CardCreate(
        type="character",
        name="Artemis",
        reference_ids=[record["id"]],
        source_refs=[{"filename": "Falsa fonte.pdf", "page": 1}],
        attributes={
            "privilegi": [
                {"reference_id": record["id"], "nome": "Tiratore scelto"},
                {"nome": "Scelta manuale"},
            ],
        },
    ), user))
    assert character.source_refs == record["source_refs"]

    linked = asyncio.run(server.create_linked_cards(
        character.id,
        server.LinkedCardInput(reference_ids=[record["id"]]),
        user,
    ))
    assert len(linked) == 1
    assert linked[0].reference_ids == [record["id"]]
    assert linked[0].source_refs == record["source_refs"]

    updated = asyncio.run(server.update_card(
        character.id,
        server.CardUpdate(reference_ids=[]),
        user,
    ))
    assert updated.source_refs == []
    assert updated.attributes["privilegi"] == [{"nome": "Scelta manuale"}]

    try:
        asyncio.run(server.create_linked_cards(
            character.id,
            server.LinkedCardInput(reference_ids=["ref-non-collegato"]),
            user,
        ))
        assert False, "Expected a rejected non-linked reference"
    except server.HTTPException as error:
        assert error.status_code == 400


def test_reference_snapshots_detect_a_corrected_source_and_preserve_manual_character_values(monkeypatch):
    original = make_reference(
        "Disciplina di ferro",
        reference_type="class",
        attributes={"dado_vita": "d10", "tiri_salvezza": "Forza, Costituzione"},
        source_text_checksum="versione-originale",
    )
    corrected = {
        **original,
        "full_text": "Il testo corretto definisce il dado vita d8 e specifica le nuove competenze.",
        "description": "Regola corretta dal manuale privato.",
        "attributes": {"dado_vita": "d8", "tiri_salvezza": "Forza, Destrezza"},
        "source_text_checksum": "versione-corretta",
    }
    references = server.MemoryCollection()
    references.rows.append(original)
    cards = server.MemoryCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=references))
    user = server.User(user_id="owner-1", email="fighter@example.com", name="Fighter")

    character = asyncio.run(server.create_card(server.CardCreate(
        type="character",
        name="Neris",
        reference_ids=[original["id"]],
        attributes={
            "classe": "Disciplina di ferro",
            "dado_vita": "d12",  # Rolled/house-rule manual choice, never overwrite.
            "tiri_salvezza": "Forza, Costituzione",
        },
    ), user))
    saved_snapshot = character.reference_snapshots[0]
    assert saved_snapshot["source_text_checksum"] == "versione-originale"
    assert reference_snapshot_changed(saved_snapshot, corrected)
    assert reference_snapshot(corrected)["content_revision"] != saved_snapshot["content_revision"]

    references.rows[0] = corrected
    report = asyncio.run(server.card_reference_updates(character.id, user))
    assert report["updated_count"] == 1
    assert report["updates"][0]["before"]["full_text"] == original["full_text"]
    assert report["updates"][0]["after"]["full_text"] == corrected["full_text"]

    refreshed = asyncio.run(server.refresh_card_reference_updates(
        character.id,
        server.ReferenceUpdateInput(reference_ids=[original["id"]]),
        user,
    ))
    assert refreshed["card"].attributes["dado_vita"] == "d12"
    assert refreshed["card"].attributes["tiri_salvezza"] == "Forza, Destrezza"
    assert "dado_vita" in refreshed["protected_fields"][original["id"]]
    assert refreshed["card"].reference_snapshots[0]["source_text_checksum"] == "versione-corretta"
    assert asyncio.run(server.card_reference_updates(character.id, user))["updated_count"] == 0


def test_untracked_reference_can_be_baselined_without_changing_card_data(monkeypatch):
    record = make_reference("Passo silenzioso", reference_type="feat", source_text_checksum="prima-versione")
    cards = server.MemoryCollection()
    cards.rows.append(server.Card(
        id="legacy-character",
        user_id="owner-1",
        type="character",
        name="Personaggio storico",
        attributes={"prerequisito": "Scelta manuale"},
        reference_ids=[record["id"]],
        source_refs=record["source_refs"],
    ).model_dump())
    references = server.MemoryCollection()
    references.rows.append(record)
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=references))
    user = server.User(user_id="owner-1", email="legacy@example.com", name="Legacy")

    report = asyncio.run(server.card_reference_updates("legacy-character", user))
    assert report["untracked_count"] == 1
    refreshed = asyncio.run(server.refresh_card_reference_updates(
        "legacy-character",
        server.ReferenceUpdateInput(reference_ids=[record["id"]]),
        user,
    ))
    assert refreshed["updated_reference_ids"] == []
    assert refreshed["card"].attributes == {"prerequisito": "Scelta manuale"}
    assert refreshed["card"].reference_snapshots[0]["reference_id"] == record["id"]


def test_attribute_only_source_correction_is_detected_and_keeps_edited_linked_entry(monkeypatch):
    original = make_reference(
        "Guardia vigile",
        reference_type="feat",
        attributes={"prerequisito": "Saggezza 13"},
        source_text_checksum="manuale-invariato",
    )
    corrected = {
        **original,
        "attributes": {"prerequisito": "Saggezza 15"},
        "source_text_checksum": "manuale-invariato",
    }
    references = server.MemoryCollection()
    references.rows.append(original)
    cards = server.MemoryCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=references))
    user = server.User(user_id="owner-1", email="rogue@example.com", name="Rogue")
    character = asyncio.run(server.create_card(server.CardCreate(
        type="character",
        name="Mira",
        reference_ids=[original["id"]],
        attributes={
            "prerequisito": "Saggezza 13",
            "privilegi": [{
                "reference_id": original["id"],
                "nome": original["name"],
                "descrizione": "Nota personale: la mia versione al tavolo.",
            }],
        },
    ), user))

    references.rows[0] = corrected
    report = asyncio.run(server.card_reference_updates(character.id, user))
    assert report["updated_count"] == 1
    assert "attributi" in report["updates"][0]["changed_fields"]

    refreshed = asyncio.run(server.refresh_card_reference_updates(
        character.id,
        server.ReferenceUpdateInput(reference_ids=[original["id"]]),
        user,
    ))
    assert refreshed["card"].attributes["prerequisito"] == "Saggezza 15"
    assert refreshed["card"].attributes["privilegi"][0]["descrizione"] == "Nota personale: la mia versione al tavolo."
    assert "privilegi" in refreshed["protected_fields"][original["id"]]


def test_legacy_snapshot_detects_attribute_correction_when_source_checksum_is_unchanged():
    original = make_reference(
        "Memoria arcana",
        reference_type="feat",
        attributes={"prerequisito": "Intelligenza 13"},
        source_text_checksum="sorgente-invariata",
    )
    legacy_snapshot = reference_snapshot(original)
    legacy_snapshot.pop("content_revision")
    corrected = {
        **original,
        "attributes": {"prerequisito": "Intelligenza 15"},
        "source_text_checksum": "sorgente-invariata",
    }

    assert reference_snapshot_changed(legacy_snapshot, corrected)


def test_public_card_projection_never_exposes_private_reference_snapshots(monkeypatch):
    record = make_reference(
        "Trama protetta",
        full_text="TESTO PRIVATO DEL MANUALE: non deve comparire su una carta condivisa.",
    )
    cards = server.MemoryCollection()
    cards.rows.append(server.Card(
        id="public-card",
        user_id="owner-1",
        type="feat",
        name="Carta pubblica",
        description="Testo sintetico della carta.",
        reference_ids=[record["id"]],
        reference_snapshots=[server.reference_snapshot_for_card(record, "feat")],
    ).model_dump())
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards))

    public_card = asyncio.run(server.public_get_card("public-card"))
    assert public_card["name"] == "Carta pubblica"
    assert "reference_snapshots" not in public_card
    assert "reference_ids" not in public_card
    assert "user_id" not in public_card
    assert "TESTO PRIVATO DEL MANUALE" not in str(public_card)


def test_apply_reference_endpoint_cannot_read_another_users_record(monkeypatch):
    record = make_reference("Tiratore Scelto", user_id="owner-1")
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=MemoryReferences([record])))
    other_user = server.User(user_id="owner-2", email="other@example.com", name="Other")

    try:
        asyncio.run(server.apply_private_reference(record["id"], other_user))
        assert False, "Expected a not-found response for another user's record"
    except server.HTTPException as error:
        assert error.status_code == 404


def test_unverified_references_cannot_be_attached_or_materialized_as_linked_cards(monkeypatch):
    record = make_reference(
        "Privilegio OCR",
        reference_type="class_feature",
        review_flags=["ocr_da_verificare"],
        review_status="needs_review",
    )
    references = server.MemoryCollection()
    references.rows.append(record)
    cards = server.MemoryCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=references))
    user = server.User(user_id="owner-1", email="ranger@example.com", name="Ranger")

    with pytest.raises(server.HTTPException, match="da verificare") as create_error:
        asyncio.run(server.create_card(server.CardCreate(
            type="character",
            name="Personaggio",
            reference_ids=[record["id"]],
        ), user))
    assert create_error.value.status_code == 409

    character = server.Card(
        id="character-1",
        user_id=user.user_id,
        type="character",
        name="Personaggio",
        reference_ids=[record["id"]],
    )
    cards.rows.append(character.model_dump())
    with pytest.raises(server.HTTPException, match="da verificare") as linked_error:
        asyncio.run(server.create_linked_cards(
            character.id,
            server.LinkedCardInput(reference_ids=[record["id"]]),
            user,
        ))
    assert linked_error.value.status_code == 409


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


def test_generate_content_labels_manual_content_without_a_trusted_source(monkeypatch):
    record = make_reference(
        "Palla di Fuoco",
        reference_type="spell",
        review_flags=["ocr_da_verificare"],
        review_status="needs_review",
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=MemoryReferences([record])))
    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago", premium_manual=True)

    monkeypatch.setattr(server, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        server.requests,
        "post",
        lambda *_args, **_kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"candidates": [{"content": {"parts": [{
                "text": '{"name":"Palla evocata","description":"Testo generato.","story":"","attributes":{}}'
            }]}}]},
        ),
    )
    payload = asyncio.run(server.generate_content(
        server.GenerateContentInput(type="spell", prompt="Palla di fuoco"),
        user,
    ))

    assert payload["source"] == "ai_generated"
    assert payload["source_status"] == "unavailable"
    assert "fonte verificata" in payload["source_message"]


def test_library_search_returns_sourced_or_explicitly_unavailable(monkeypatch):
    trusted = make_reference("Palla di Fuoco", reference_type="spell")
    unverified = make_reference(
        "Dardo Incantato",
        reference_type="spell",
        review_flags=["riga_tabella_da_verificare"],
        review_status="needs_review",
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=MemoryReferences([trusted, unverified])))
    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago")

    sourced = asyncio.run(server.search_private_library(q="Palla di fuoco", types="spell", user=user))
    unavailable = asyncio.run(server.search_private_library(q="Dardo incantato", types="spell", user=user))
    diagnostic = asyncio.run(server.search_private_library(
        q="Dardo incantato",
        types="spell",
        include_unverified=True,
        user=user,
    ))

    assert sourced["status"] == "sourced"
    assert sourced["records"][0]["is_trusted"] is True
    assert unavailable["status"] == "unavailable"
    assert "fonte verificata" in unavailable["message"]
    assert diagnostic["records"][0]["needs_review"] is True


def test_library_review_search_scopes_manuals_and_filters_before_result_limit(monkeypatch, tmp_path):
    manual_a = tmp_path / "Manuale-A.pdf"
    manual_b = tmp_path / "Manuale-B.pdf"
    manual_a.write_bytes(b"manual a")
    manual_b.write_bytes(b"manual b")
    verified_records = [
        make_reference(
            f"Archivio {index:02}",
            reference_type="class",
            source_refs=[{"filename": "Manuale-A.pdf", "page": index + 1}],
        )
        for index in range(45)
    ]
    review_in_a = make_reference(
        "Zeta da verificare",
        reference_type="class",
        source_refs=[{"filename": "Manuale-A.pdf", "page": 99}],
        review_flags=["ocr_da_verificare"],
        review_status="needs_review",
    )
    review_in_b = make_reference(
        "Altra revisione",
        reference_type="class",
        source_refs=[{"filename": "Manuale-B.pdf", "page": 12}],
        review_flags=["ocr_da_verificare"],
        review_status="needs_review",
    )
    monkeypatch.setattr(
        server,
        "available_reference_manuals",
        lambda: {"Manuale-A.pdf": manual_a, "Manuale-B.pdf": manual_b},
    )
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(private_reference_records=MemoryReferences([
            *verified_records,
            review_in_a,
            review_in_b,
            {**review_in_a, "id": "other-owner-record", "user_id": "owner-2"},
        ])),
    )
    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago")

    result = asyncio.run(server.search_private_library(
        q="",
        types="class",
        review_only=True,
        include_unverified=True,
        source_filename="Manuale-A.pdf",
        user=user,
    ))

    assert [record["id"] for record in result["records"]] == [review_in_a["id"]]
    assert result["records"][0]["needs_review"] is True


def test_manual_coverage_counts_valid_missing_and_records_to_review(monkeypatch, tmp_path):
    source = tmp_path / "Manuale.pdf"
    source.write_bytes(b"manual")
    records = [
        make_reference(
            "Guerriero",
            reference_type="class",
            source_refs=[{"filename": "Manuale.pdf", "page": 10}],
        ),
        make_reference(
            "Campione",
            reference_type="subclass",
            source_refs=[{"filename": "Manuale.pdf", "page": 11}],
            review_flags=["sezione_potenzialmente_continua"],
            review_status="needs_review",
        ),
    ]
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {"Manuale.pdf": source})
    monkeypatch.setattr(server, "MANUAL_COVERAGE_CATEGORIES", {"Manuale.pdf": ("class", "subclass", "spell")})

    report = server.manual_coverage_report(records)
    coverage = {item["reference_type"]: item for item in report[0]["categories"]}

    assert coverage["class"] == {"reference_type": "class", "valid": 1, "to_review": 0, "missing": 0, "records_total": 1}
    assert coverage["subclass"] == {"reference_type": "subclass", "valid": 0, "to_review": 1, "missing": 0, "records_total": 1}
    assert coverage["spell"] == {"reference_type": "spell", "valid": 0, "to_review": 0, "missing": 1, "records_total": 0}


def test_apply_reference_rejects_unverified_records(monkeypatch):
    record = make_reference(
        "Rituale Incerto",
        reference_type="spell",
        review_flags=["traduzione_da_verificare"],
        review_status="needs_review",
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=MemoryReferences([record])))
    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago")

    with pytest.raises(server.HTTPException, match="dato certo") as error:
        asyncio.run(server.apply_private_reference(record["id"], user))

    assert error.value.status_code == 409


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


def test_manual_metadata_uses_the_same_ocr_rule_as_imports():
    assert server.manual_requires_ocr("Manuale_del_giocatore__1787259882002.pdf")
    assert server.manual_requires_ocr("Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf")
    assert server.manual_requires_ocr("724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf")
    assert not server.manual_requires_ocr("Guida_onnicomprensiva_di_Xanathar__1787259928030.pdf")
    assert not server.manual_requires_ocr("731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf")


def test_spanish_parser_recognizes_classes_feats_and_equipment_without_ocr():
    page = """BárBaro
Un feroz guerrero de origen primitivo que puede dejarse llevar por la furia en
combate. Esta descripción conserva suficientes detalles para identificar la
clase y permitir una traducción posterior sin utilizar OCR.
TALENTO DE GUERRA
Prerequisito: Fuerza 13. Esta dote mejora el combate y concede una ventaja
concreta que debe conservarse para la revisión del texto fuente.
ARMAS
Espada larga 15 po 1d8 cortante 1,5 kg
ARMADURAS
Armadura de cuero 10 po CA 11 5 kg
Escudo 10 po CA +2 3 kg
"""
    records = parse_reference_page(page, "Manual del Jugador.pdf", 74, "es")
    by_name = {record["name"]: record for record in records}

    assert by_name["Bárbaro"]["reference_type"] == "class"
    assert by_name["Talento De Guerra"]["reference_type"] == "feat"
    assert by_name["Talento De Guerra"]["attributes"]["prerequisito"] == "Fuerza 13"
    assert by_name["Espada Larga"]["reference_type"] == "weapon"
    assert by_name["Espada Larga"]["attributes"]["costo"] == "15 po"
    assert by_name["Espada Larga"]["attributes"]["tipo_danno"] == "cortante"
    assert by_name["Armadura De Cuero"]["reference_type"] == "armor"
    assert by_name["Escudo"]["reference_type"] == "shield"
    assert by_name["Bárbaro"]["source_refs"] == [{
        "filename": "Manual del Jugador.pdf", "page": 74, "language": "es",
    }]


def test_spanish_translation_uses_only_structured_fields_and_requires_complete_json(monkeypatch):
    captured = {}

    class TranslationResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": """
{"records":[{"id":"ref-es","name":"Barbaro","description":"Un guerriero feroce.","full_text":"Un guerriero feroce con tutto il testo tradotto.","attributes":{"livello":"1"}}]}
"""}]}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return TranslationResponse()

    monkeypatch.setattr(server, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(server.requests, "post", fake_post)
    translated, error = server.translate_spanish_reference_batch([{
        "id": "ref-es",
        "source_name": "Bárbaro",
        "source_description": "Un guerrero feroz.",
        "source_full_text": "Questo testo sorgente completo viene tradotto.",
        "source_attributes": {"livello": "1"},
    }])

    assert error == ""
    assert translated["ref-es"]["name"] == "Barbaro"
    assert translated["ref-es"]["attributes"] == {"livello": "1"}
    prompt = captured["json"]["contents"][0]["parts"][0]["text"]
    assert "Questo testo sorgente completo viene tradotto" in prompt
    assert translated["ref-es"]["full_text"] == "Un guerriero feroce con tutto il testo tradotto."
    assert captured["url"].endswith("/models/gemini-3.6-flash:generateContent")


def test_spanish_import_reuses_translation_and_keeps_source_text(monkeypatch, tmp_path):
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    record = make_reference(
        "Bárbaro",
        reference_type="class",
        description="Un guerrero feroz de origen primitivo.",
        full_text="Un guerrero feroz de origen primitivo que combate con furia.",
    )
    collection = MutableMemoryReferences([])
    calls = []
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(
        server,
        "available_reference_manuals",
        lambda: {"731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf": source},
    )
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[record], pages_read=1, pages_needing_ocr=[]),
    )

    def translate(batch):
        calls.append(batch)
        return {
            batch[0]["id"]: {
                "name": "Barbaro",
                "description": "Un guerriero feroce di origine primitiva.",
                "full_text": "Un guerriero feroce di origine primitiva che combatte con furia.",
                "attributes": {},
            }
        }, ""

    monkeypatch.setattr(server, "translate_spanish_reference_batch", translate)
    body = server.ReferenceImportInput(
        filenames=["731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"],
        translation_processing_confirmed=True,
        start_page=5,
        end_page=5,
    )
    first = asyncio.run(server.import_private_reference_manuals("owner-1", body))
    second = asyncio.run(server.import_private_reference_manuals("owner-1", body))

    assert first.imported == 1
    assert second.updated == 1
    assert len(calls) == 1
    stored = collection.rows[0]
    assert stored["name"] == "Barbaro"
    assert stored["source_language"] == "es"
    assert stored["source_name"] == "Bárbaro"
    assert stored["source_full_text"].startswith("Un guerrero feroz")
    assert stored["full_text"].startswith("Un guerriero feroce")
    assert stored["translation_status"] == "translated"
    assert second.sources[0]["translation_reused"] == 1


def test_spanish_translation_failure_is_saved_for_review(monkeypatch, tmp_path):
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    collection = MutableMemoryReferences([])
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(
        server,
        "available_reference_manuals",
        lambda: {"731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf": source},
    )
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[make_reference("Bárbaro", reference_type="class")], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(server, "translate_spanish_reference_batch", lambda batch: ({}, "provider_translation_failed"))

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=["731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=5,
        ),
    ))

    assert result.flagged_for_review == 1
    assert result.sources[0]["translation_failed"] == 1
    assert collection.rows[0]["translation_status"] == "failed"
    assert collection.rows[0]["translation_error"] == "provider_translation_failed"
    assert "traduzione_da_verificare" in collection.rows[0]["review_flags"]


def test_retry_single_failed_spanish_translation_preserves_source_fields(monkeypatch):
    source = {
        **make_reference(
            "Bárbaro",
            reference_type="class",
            normalized_name="barbaro",
            description="Un guerrero feroz.",
            full_text="Un guerrero feroz que combate con furia.",
            attributes={"dado_vita": "d12"},
            source_language="es",
            source_key="Manual-del-Jugador.pdf",
            source_normalized_name="barbaro",
            source_name="Bárbaro",
            source_description="Un guerrero feroz.",
            source_full_text="Un guerrero feroz que combate con furia.",
            source_attributes={"dado_vita": "d12"},
            source_text_checksum="source-checksum",
            translation_status="failed",
            translation_error="provider_translation_failed",
            review_flags=["traduzione_da_verificare"],
            review_status="needs_review",
        ),
        "id": "ref-owned-barbaro",
    }
    collection = MutableMemoryReferences([source])
    calls = []

    def translate(batch):
        calls.append(batch)
        assert batch[0]["id"] == source["id"]
        assert batch[0]["source_name"] == "Bárbaro"
        assert batch[0]["source_full_text"] == source["source_full_text"]
        return {
            source["id"]: {
                "name": "Barbaro",
                "description": "Un guerriero feroce.",
                "full_text": "Un guerriero feroce che combatte con furia.",
                "attributes": {"dado_vita": "d12"},
            }
        }, ""

    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "translate_spanish_reference_batch", translate)

    result = asyncio.run(server.retry_private_reference_translation("owner-1", source["id"]))

    assert len(calls) == 1
    assert result["id"] == source["id"]
    assert result["source_language"] == "es"
    assert result["source_name"] == "Bárbaro"
    assert result["source_full_text"] == source["source_full_text"]
    assert result["source_key"] == source["source_key"]
    assert result["name"] == "Barbaro"
    assert result["translation_status"] == "translated"
    assert result["translation_error"] == ""
    assert result["review_flags"] == []
    assert result["review_status"] == "pending"


def test_concurrent_translation_retries_share_one_provider_call_and_return_completed_record(monkeypatch):
    source = {
        **make_reference(
            "Bárbaro",
            reference_type="class",
            normalized_name="barbaro",
            description="Un guerrero feroz.",
            full_text="Un guerrero feroz que combate con furia.",
            source_language="es",
            source_key="Manual-del-Jugador.pdf",
            source_normalized_name="barbaro",
            source_name="Bárbaro",
            source_description="Un guerrero feroz.",
            source_full_text="Un guerrero feroz que combate con furia.",
            source_attributes={"dado_vita": "d12"},
            translation_status="failed",
            translation_error="provider_translation_failed",
            review_flags=["traduzione_da_verificare"],
            review_status="needs_review",
        ),
        "id": "ref-owned-barbaro",
    }
    collection = MutableMemoryReferences([source])
    provider_started = threading.Event()
    allow_provider_result = threading.Event()
    calls = []

    def translate(batch):
        calls.append(batch)
        provider_started.set()
        assert allow_provider_result.wait(timeout=2), "The test did not release the provider"
        return {
            source["id"]: {
                "name": "Barbaro",
                "description": "Un guerriero feroce.",
                "full_text": "Un guerriero feroce che combatte con furia.",
                "attributes": {"dado_vita": "d12"},
            }
        }, ""

    async def retry_from_two_devices():
        first = asyncio.create_task(
            server.retry_private_reference_translation("owner-1", source["id"])
        )
        assert await asyncio.to_thread(provider_started.wait, 1)
        second = asyncio.create_task(
            server.retry_private_reference_translation("owner-1", source["id"])
        )
        await asyncio.sleep(0.1)
        assert len(calls) == 1
        allow_provider_result.set()
        return await asyncio.gather(first, second)

    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "translate_spanish_reference_batch", translate)

    first_result, second_result = asyncio.run(retry_from_two_devices())

    assert len(calls) == 1
    assert first_result == second_result
    assert second_result["translation_status"] == "translated"
    assert second_result["name"] == "Barbaro"
    assert second_result["source_language"] == "es"
    assert second_result["source_full_text"] == source["source_full_text"]
    assert second_result["source_refs"] == source["source_refs"]
    assert collection.rows[0]["translation_status"] == "translated"
    assert collection.rows[0]["source_refs"] == source["source_refs"]


def test_retry_reclaims_an_abandoned_translation_lease(monkeypatch):
    source = {
        **make_reference(
            "Bárbaro",
            reference_type="class",
            source_language="es",
            source_key="Manual-del-Jugador.pdf",
            source_normalized_name="barbaro",
            source_name="Bárbaro",
            source_description="Un guerrero feroz.",
            source_full_text="Un guerrero feroz que combate con furia.",
            source_attributes={"dado_vita": "d12"},
            translation_status="processing",
            translation_lease_id="abandoned-request",
            translation_lease_expires_at=0,
        ),
        "id": "ref-owned-barbaro",
    }
    collection = MutableMemoryReferences([source])
    calls = []

    def translate(batch):
        calls.append(batch)
        return {
            source["id"]: {
                "name": "Barbaro",
                "description": "Un guerriero feroce.",
                "full_text": "Un guerriero feroce che combatte con furia.",
                "attributes": {"dado_vita": "d12"},
            }
        }, ""

    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "translate_spanish_reference_batch", translate)

    result = asyncio.run(server.retry_private_reference_translation("owner-1", source["id"]))

    assert len(calls) == 1
    assert result["translation_status"] == "translated"
    assert result["translation_lease_id"] == ""
    assert result["translation_lease_expires_at"] == 0
    assert result["source_language"] == "es"
    assert result["source_full_text"] == source["source_full_text"]
    assert result["source_refs"] == source["source_refs"]


def test_retry_failed_translation_keeps_source_when_provider_fails(monkeypatch):
    source = {
        **make_reference(
            "Bárbaro",
            reference_type="class",
            normalized_name="barbaro",
            description="Testo sorgente.",
            full_text="Testo sorgente spagnolo da verificare.",
            source_language="es",
            source_key="Manual-del-Jugador.pdf",
            source_normalized_name="barbaro",
            source_name="Bárbaro",
            source_description="Texto fuente.",
            source_full_text="Texto fuente español que debe permanecer.",
            source_attributes={"dado_vita": "d12"},
            translation_status="failed",
            translation_error="provider_translation_failed",
            review_flags=["traduzione_da_verificare"],
            review_status="needs_review",
        ),
        "id": "ref-owned-barbaro",
    }
    collection = MutableMemoryReferences([source])
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(
        server,
        "translate_spanish_reference_batch",
        lambda batch: ({}, "provider_translation_invalid"),
    )

    result = asyncio.run(server.retry_private_reference_translation("owner-1", source["id"]))

    assert result["translation_status"] == "failed"
    assert result["translation_error"] == "provider_translation_invalid"
    assert result["name"] == "Bárbaro"
    assert result["full_text"] == "Testo sorgente spagnolo da verificare."
    assert result["source_name"] == "Bárbaro"
    assert result["source_full_text"] == "Texto fuente español que debe permanecer."
    assert result["source_language"] == "es"
    assert result["review_status"] == "needs_review"
    assert "traduzione_da_verificare" in result["review_flags"]
    assert result["translation_lease_id"] == ""
    assert result["translation_lease_expires_at"] == 0


def test_retry_translated_record_does_not_call_provider_or_modify_record(monkeypatch):
    source = {
        **make_reference(
            "Barbaro",
            reference_type="class",
            source_language="es",
            translation_status="translated",
            translation_error="",
        ),
        "id": "ref-owned-barbaro",
    }
    collection = MutableMemoryReferences([source])
    calls = []
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "translate_spanish_reference_batch", lambda batch: calls.append(batch))

    result = asyncio.run(server.retry_private_reference_translation("owner-1", source["id"]))

    assert result == source
    assert calls == []


def test_retry_translation_endpoint_rejects_non_premium_user_before_provider_call(monkeypatch):
    calls = []

    async def non_premium_user():
        return server.User(user_id="owner-1", email="ranger@example.com", name="Ranger")

    monkeypatch.setattr(server, "translate_spanish_reference_batch", lambda batch: calls.append(batch))
    server.app.dependency_overrides[server.get_current_user] = non_premium_user
    try:
        with TestClient(server.app) as client:
            response = client.post("/api/library/ref-owned-barbaro/translation-retry")
    finally:
        server.app.dependency_overrides.pop(server.get_current_user, None)

    assert response.status_code == 402
    assert calls == []


def test_spanish_manual_rejects_ocr_even_when_the_request_is_confirmed(monkeypatch, tmp_path):
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})

    try:
        asyncio.run(server.import_private_reference_manuals(
            "owner-1",
            server.ReferenceImportInput(
                filenames=[filename],
                use_ai_ocr=True,
                external_processing_confirmed=True,
                translation_processing_confirmed=True,
                start_page=5,
                end_page=6,
            ),
        ))
        assert False, "Expected native Spanish manual to reject OCR"
    except server.HTTPException as error:
        assert error.status_code == 400
        assert "testo nativo" in error.detail


def test_spanish_translation_requires_consent_before_provider_call(monkeypatch, tmp_path):
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    calls = []
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(server, "translate_spanish_reference_batch", lambda batch: calls.append(batch))

    try:
        asyncio.run(server.import_private_reference_manuals(
            "owner-1",
            server.ReferenceImportInput(filenames=[filename]),
        ))
        assert False, "Expected translation consent failure"
    except server.HTTPException as error:
        assert error.status_code == 400
        assert "testo estratto" in error.detail
    assert calls == []


def test_spanish_import_requires_a_small_native_page_range(monkeypatch, tmp_path):
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})

    for body in (
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
        ),
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=17,
        ),
    ):
        try:
            asyncio.run(server.import_private_reference_manuals("owner-1", body))
            assert False, "Expected bounded translation range failure"
        except server.HTTPException as error:
            assert error.status_code == 400
            assert "12 pagine" in error.detail


def test_translated_reference_payload_marks_italian_content_language():
    payload = reference_to_card_payload(make_reference(
        "Barbaro",
        reference_type="class",
        source_language="es",
        translation_status="translated",
    ))

    assert payload["source_language"] == "es"
    assert payload["content_language"] == "it"


def test_spanish_spell_parser_extracts_native_quick_fields_for_spell_cards():
    page = """ABrIr
Transmutación nivel 2
Tiempo de lanzamiento: 1 acción
Alcance: 60 pies
Componentes: V
Duración: Instantáneo
Elige un objeto que puedas ver dentro del alcance. Este conjuro mantiene una
descripción suficiente para la carta italiana y para revisar el texto fuente.
"""
    records = parse_reference_page(page, "Manual del Jugador.pdf", 487, "es")

    assert len(records) == 1
    assert records[0]["reference_type"] == "spell"
    assert records[0]["attributes"] == {
        "scuola": "Transmutación",
        "livello": "2",
        "tempo_lancio": "1 acción",
        "gittata": "60 pies",
        "componenti": "V",
        "durata": "Instantáneo",
    }
    assert reference_to_card_payload({**records[0], "translation_status": "translated"})["card_type"] == "spell"


def test_spanish_spell_parser_keeps_consecutive_spell_blocks_separate():
    page = """ABrIr
Transmutación nivel 2
Tiempo de lanzamiento: 1 acción
Alcance: 60 pies
Componentes: V
Duración: Instantáneo
Elige una puerta cerrada y ábrela mediante magia.
ACELErar
Transmutación nivel 3
Tiempo de lanzamiento: 1 acción
Alcance: 30 pies
Componentes: V, S, M
Duración: Concentración, hasta 1 minuto
Elige una criatura voluntaria y duplica su velocidad.
"""
    records = parse_reference_page(page, "Manual del Jugador.pdf", 488, "es")
    by_name = {record["name"]: record for record in records}

    assert set(by_name) == {"Abrir", "Acelerar"}
    assert "Acelerar" not in by_name["Abrir"]["full_text"]
    assert "Abrir" not in by_name["Acelerar"]["full_text"]
    assert by_name["Abrir"]["attributes"]["gittata"] == "60 pies"
    assert by_name["Acelerar"]["attributes"]["durata"] == "Concentración, hasta 1 minuto"
