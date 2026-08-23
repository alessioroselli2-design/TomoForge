import asyncio
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

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


def test_reference_parser_recognizes_spanish_feats_and_subraces_from_small_caps_titles():
    feat_record = parse_reference_page(
        """MENtE AGUda
Requisitos: Inteligencia 13 o más. Posees una mente con una capacidad asombrosa
para percibir el paso del tiempo, orientarse y recordar hasta el más mínimo detalle.
Obtienes los beneficios siguientes: tu puntuación de Inteligencia aumenta en 1.
""",
        "Manual del Jugador.pdf",
        345,
        "es",
    )[0]
    subrace_record = parse_reference_page(
        """ENaNo dE Las CoLINas
Como enano de las colinas, posees sentidos agudos, una profunda intuición y
una resistencia notable. Tu puntuación de Sabiduría aumenta en 1 y tus puntos
de golpe máximos aumentan en 1 cada vez que subes de nivel.
""",
        "Manual del Jugador.pdf",
        32,
        "es",
    )[0]

    assert feat_record["reference_type"] == "feat"
    assert feat_record["attributes"]["prerequisito"] == "Inteligencia 13 o más"
    assert subrace_record["reference_type"] == "subrace"
    assert subrace_record["source_refs"] == [{
        "filename": "Manual del Jugador.pdf",
        "page": 32,
        "language": "es",
    }]


def test_reference_parser_skips_sparse_spanish_index_entries_that_match_feat_titles():
    index_page = "\n".join([
        "Página 955",
        "Acechador",
        "Actor",
        "Afortunado",
        "Alerta",
        "Alineamiento",
        "Alquimia",
        "Alterar el propio aspecto",
        "Amistad",
        "Ancestro Dragón",
        "Animar objetos",
        "Antipatía",
        "Apariencia",
        "Aprender conjuros",
        "Armaduras",
        "Armas",
        "Arquetipos",
        "Atributos",
        "Atacante salvaje",
        "Atleta",
        "Aura de vida",
        "Aventuras",
        "Avance de personajes",
        "Azote de magos",
        "Bardo",
        "Bendición",
        "Bola de fuego",
    ])

    records = parse_reference_page(index_page, "Manual del Jugador.pdf", 955, "es")

    assert not [record for record in records if record["reference_type"] == "feat"]


def test_reference_extractor_joins_spanish_feat_heading_with_its_next_page(tmp_path):
    import fitz
    from reference_library import extract_reference_records

    pdf_path = tmp_path / "manual-del-jugador.pdf"
    document = fitz.open()
    first = document.new_page()
    first.insert_text(
        (72, 72),
        """La descripción previa conserva suficiente texto nativo para que la página
pueda procesarse, pero no contiene otra regla ni otro encabezado reconocible.
LÍDER INSPIRADOR""",
    )
    second = document.new_page()
    second.insert_text(
        (72, 72),
        """Requisitos: Carisma 13 o más. Puedes invertir diez minutos en inspirar a
tus compañeros, apuntalando su voluntad para luchar y continuar la aventura.
Obtienes los beneficios siguientes: cada aliado recibe puntos de golpe temporales.
LIGERAMENTE ACORAZADO
Has entrenado tu cuerpo para llevar armaduras ligeras sin perder movilidad.""",
    )
    document.save(pdf_path)
    document.close()

    report = extract_reference_records(pdf_path, source_language="es")
    leader = next(record for record in report.records if record["name"] == "Líder Inspirador")

    assert leader["reference_type"] == "feat"
    assert leader["source_refs"] == [{
        "filename": "manual-del-jugador.pdf",
        "page": 1,
        "language": "es",
    }]
    assert "sezione_potenzialmente_continua" not in leader["review_flags"]


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


def test_reference_merge_deduplicates_identical_native_rules_across_manuals():
    first = make_reference(
        "Palla di Fuoco",
        reference_type="spell",
        source_key="Manuale-del-Giocatore.pdf",
        source_language="it",
        source_refs=[{"filename": "Manuale-del-Giocatore.pdf", "page": 241}],
        attributes={"livello": "3", "scuola": "Evocazione"},
    )
    second = make_reference(
        "Palla di fuoco",
        reference_type="spell",
        source_key="Guida-di-Xanathar.pdf",
        source_language="it",
        source_refs=[{"filename": "Guida-di-Xanathar.pdf", "page": 155}],
        attributes={"livello": "3", "scuola": "Evocazione"},
    )

    merged = merge_reference_records([first, second])

    assert len(merged) == 1
    assert merged[0]["source_refs"] == [
        {"filename": "Manuale-del-Giocatore.pdf", "page": 241},
        {"filename": "Guida-di-Xanathar.pdf", "page": 155},
    ]


def test_reference_merge_keeps_rule_variants_from_different_manuals_separate():
    first = make_reference(
        "Palla di Fuoco",
        reference_type="spell",
        source_key="Manuale-del-Giocatore.pdf",
        source_language="it",
        full_text="Una sfera infuocata infligge 8d6 danni da fuoco.",
        attributes={"livello": "3", "danni": "8d6"},
    )
    revised = make_reference(
        "Palla di Fuoco",
        reference_type="spell",
        source_key="Manuale-rivisto.pdf",
        source_language="it",
        full_text="Una sfera infuocata infligge 10d6 danni da fuoco.",
        attributes={"livello": "3", "danni": "10d6"},
    )

    assert len(merge_reference_records([first, revised])) == 2


def test_reference_search_hides_existing_cross_manual_duplicates():
    first = make_reference(
        "Palla di Fuoco",
        reference_type="spell",
        source_key="Manuale-del-Giocatore.pdf",
        source_language="it",
        source_refs=[{"filename": "Manuale-del-Giocatore.pdf", "page": 241}],
        attributes={"livello": "3", "scuola": "Evocazione"},
    )
    second = make_reference(
        "Palla di Fuoco",
        reference_type="spell",
        source_key="Guida-di-Xanathar.pdf",
        source_language="it",
        source_refs=[{"filename": "Guida-di-Xanathar.pdf", "page": 155}],
        attributes={"livello": "3", "scuola": "Evocazione"},
    )

    matches = search_reference_records([first, second], "palla di fuoco")

    assert len(matches) == 1
    assert len(matches[0]["source_refs"]) == 2


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
    assert character.rule_sources == [{
        "source_kind": "reference",
        "source_id": record["id"],
        "name": record["name"],
        "reference_type": record["reference_type"],
        "source_refs": record["source_refs"],
    }]
    assert "description" not in character.reference_snapshots[0]
    assert "full_text" not in character.reference_snapshots[0]

    linked = asyncio.run(server.create_linked_cards(
        character.id,
        server.LinkedCardInput(reference_ids=[record["id"]], version=character.version),
        user,
    ))
    assert len(linked) == 1
    assert linked[0].reference_ids == [record["id"]]
    assert linked[0].source_refs == record["source_refs"]
    assert linked[0].rule_sources[0]["name"] == record["name"]

    current_character = asyncio.run(server.get_card(character.id, user))
    updated = asyncio.run(server.update_card(
        character.id,
        server.CardUpdate(reference_ids=[], version=current_character.version),
        user,
    ))
    assert updated.source_refs == []
    assert updated.rule_sources == []
    assert updated.attributes["privilegi"] == [{"nome": "Scelta manuale"}]
    restored = asyncio.run(server.undo_card_change(
        character.id,
        server.CardVersionInput(version=updated.version),
        user,
    ))
    assert restored["card"].reference_ids == [record["id"]]
    assert restored["card"].rule_sources[0]["source_id"] == record["id"]
    snapshot = restored["entry"]["before"]["reference_snapshots"][0]
    assert "description" not in snapshot
    assert "full_text" not in snapshot

    try:
        asyncio.run(server.create_linked_cards(
            character.id,
            server.LinkedCardInput(reference_ids=["ref-non-collegato"], version=updated.version),
            user,
        ))
        assert False, "Expected a rejected non-linked reference"
    except server.HTTPException as error:
        assert error.status_code == 400


def test_linked_card_creation_removes_partial_set_when_persistence_fails(monkeypatch):
    first = make_reference("Tiratore scelto")
    second = make_reference("Sentinella")
    references = server.MemoryCollection()
    references.rows.extend([first, second])

    class FailingLinkedCardCollection(server.MemoryCollection):
        async def insert_many(self, documents):
            # Simulate a backend failure after its first child row was written.
            await self.insert_one(documents[0])
            raise RuntimeError("Errore di persistenza della seconda carta")

    cards = FailingLinkedCardCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=references))
    user = server.User(user_id="owner-1", email="ranger@example.com", name="Ranger")
    character = asyncio.run(server.create_card(server.CardCreate(
        type="character",
        name="Artemis",
        reference_ids=[first["id"], second["id"]],
    ), user))

    with pytest.raises(RuntimeError, match="Errore di persistenza"):
        asyncio.run(server.create_linked_cards(
            character.id,
            server.LinkedCardInput(
                reference_ids=[first["id"], second["id"]],
                version=character.version,
            ),
            user,
        ))

    assert [card for card in cards.rows if card["type"] != "character"] == []
    restored_character = asyncio.run(server.get_card(character.id, user))
    assert restored_character.version == character.version


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
    assert "full_text" not in report["updates"][0]["before"]
    assert "full_text" not in report["updates"][0]["after"]
    assert "testo" in report["updates"][0]["changed_fields"]

    refreshed = asyncio.run(server.refresh_card_reference_updates(
        character.id,
        server.ReferenceUpdateInput(reference_ids=[original["id"]], version=character.version),
        user,
    ))
    assert refreshed["card"].attributes["dado_vita"] == "d12"
    assert refreshed["card"].attributes["tiri_salvezza"] == "Forza, Destrezza"
    assert "dado_vita" in refreshed["protected_fields"][original["id"]]
    assert refreshed["card"].reference_snapshots[0]["source_text_checksum"] == "versione-corretta"
    assert asyncio.run(server.card_reference_updates(character.id, user))["updated_count"] == 0


def test_card_history_keeps_manual_and_user_changes_separate_and_account_scoped(monkeypatch):
    cards = server.MemoryCollection()
    reference = make_reference(
        "Guerriero",
        reference_type="class",
        attributes={"dado_vita": "d10", "tiri_salvezza": "Forza, Costituzione"},
    )
    references = server.MemoryCollection()
    references.rows.append(reference)
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=references))
    owner = server.User(user_id="owner-1", email="owner@example.com", name="Owner")
    other_user = server.User(user_id="owner-2", email="other@example.com", name="Other")

    character = asyncio.run(server.create_card(server.CardCreate(
        type="character",
        name="Neris",
        reference_ids=[reference["id"]],
        attributes={"classe": "Guerriero", "punti_ferita": "18", "dadi_vita": "d10"},
    ), owner))
    user_saved = asyncio.run(server.update_card(
        character.id,
        server.CardUpdate(
            attributes={"classe": "Guerriero", "punti_ferita": "18", "dadi_vita": "d12", "pf_attuali": "14"},
            version=character.version,
        ),
        owner,
    ))
    assert user_saved.change_history[-1]["source"] == "user"
    assert user_saved.change_history[-1]["changed_fields"] == ["attributes"]

    manual_saved = asyncio.run(server.complete_card_from_manuals(
        character.id,
        server.ManualCompletionInput(version=user_saved.version),
        owner,
    ))
    assert manual_saved.change_history[-1]["source"] == "manual"
    assert manual_saved.change_history[-1]["action"] == "manual_completion"

    undone = asyncio.run(server.undo_card_change(
        character.id, server.CardVersionInput(version=manual_saved.version), owner,
    ))
    assert undone["card"].attributes["dadi_vita"] == "d12"
    assert undone["card"].attributes["pf_attuali"] == "14"
    assert "tiri_salvezza" not in undone["card"].attributes
    assert undone["history"][-1]["undone"] is True

    redone = asyncio.run(server.redo_card_change(
        character.id, server.CardVersionInput(version=undone["card"].version), owner,
    ))
    assert redone["card"].attributes["tiri_salvezza"] == "Forza, Costituzione"
    assert redone["card"].attributes["pf_attuali"] == "14"

    try:
        asyncio.run(server.card_history(character.id, other_user))
        assert False, "Expected the other account not to access this card history"
    except server.HTTPException as error:
        assert error.status_code == 404


def test_card_history_redo_follows_undo_order_and_drops_stale_branches(monkeypatch):
    cards = server.MemoryCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=server.MemoryCollection()))
    user = server.User(user_id="owner-1", email="owner@example.com", name="Owner")
    character = asyncio.run(server.create_card(server.CardCreate(
        type="character", name="Neris", attributes={"pf_attuali": "18"},
    ), user))

    first = asyncio.run(server.update_card(character.id, server.CardUpdate(attributes={"pf_attuali": "14"}, version=character.version), user))
    second = asyncio.run(server.update_card(character.id, server.CardUpdate(attributes={"pf_attuali": "9"}, version=first.version), user))
    assert first.version == 1
    assert second.version == 2

    undo_second = asyncio.run(server.undo_card_change(character.id, server.CardVersionInput(version=second.version), user))
    assert undo_second["card"].attributes["pf_attuali"] == "14"
    undo_first = asyncio.run(server.undo_card_change(character.id, server.CardVersionInput(version=undo_second["card"].version), user))
    assert undo_first["card"].attributes["pf_attuali"] == "18"
    redo_first = asyncio.run(server.redo_card_change(character.id, server.CardVersionInput(version=undo_first["card"].version), user))
    assert redo_first["card"].attributes["pf_attuali"] == "14"
    redo_second = asyncio.run(server.redo_card_change(character.id, server.CardVersionInput(version=redo_first["card"].version), user))
    assert redo_second["card"].attributes["pf_attuali"] == "9"

    undo_for_branch = asyncio.run(server.undo_card_change(character.id, server.CardVersionInput(version=redo_second["card"].version), user))
    asyncio.run(server.update_card(character.id, server.CardUpdate(attributes={"pf_attuali": "7"}, version=undo_for_branch["card"].version), user))
    try:
        asyncio.run(server.redo_card_change(character.id, server.CardVersionInput(version=undo_for_branch["card"].version + 1), user))
        assert False, "Expected a new edit to invalidate the redo branch"
    except server.HTTPException as error:
        assert error.status_code == 409


def test_card_update_rejects_a_stale_editor_version_without_changing_history(monkeypatch):
    cards = server.MemoryCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=server.MemoryCollection()))
    user = server.User(user_id="owner-1", email="owner@example.com", name="Owner")
    character = asyncio.run(server.create_card(server.CardCreate(
        type="character", name="Neris", attributes={"pf_attuali": "18", "tiri_salvezza": "Forza"},
    ), user))
    stale_version = character.version
    saved = asyncio.run(server.update_card(
        character.id,
        server.CardUpdate(attributes={"pf_attuali": "14", "tiri_salvezza": "Forza"}, version=stale_version),
        user,
    ))

    try:
        asyncio.run(server.update_card(
            character.id,
            server.CardUpdate(attributes={"pf_attuali": "18", "tiri_salvezza": "Destrezza"}, version=stale_version),
            user,
        ))
        assert False, "Expected the stale save to be rejected"
    except server.HTTPException as error:
        assert error.status_code == 409

    persisted = asyncio.run(server.get_card(character.id, user))
    assert persisted.attributes == {"pf_attuali": "14", "tiri_salvezza": "Forza"}
    assert persisted.change_history == saved.change_history


def test_card_mutation_requests_require_a_non_negative_read_version():
    for model, payload in (
        (server.CardUpdate, {"name": "Carta"}),
        (server.LinkedCardInput, {"reference_ids": []}),
        (server.ReferenceUpdateInput, {"reference_ids": []}),
        (server.ManualCompletionInput, {}),
        (server.CardVersionInput, {}),
    ):
        with pytest.raises(ValidationError):
            model(**payload)
        with pytest.raises(ValidationError):
            model(**{**payload, "version": -1})


def test_versioned_card_mutations_reject_stale_concurrent_actions(monkeypatch):
    """Every mutation path must reject the second action from the same read."""
    reference = make_reference("Tiratore scelto")
    cards = server.MemoryCollection()
    references = server.MemoryCollection()
    references.rows.append(reference)
    monkeypatch.setattr(server, "db", SimpleNamespace(cards=cards, private_reference_records=references))
    user = server.User(user_id="owner-1", email="owner@example.com", name="Owner")

    def assert_conflict(awaitable):
        with pytest.raises(server.HTTPException) as error:
            asyncio.run(awaitable)
        assert error.value.status_code == 409

    manual_card = asyncio.run(server.create_card(server.CardCreate(type="character", name="Manuale"), user))
    completed = asyncio.run(server.complete_card_from_manuals(
        manual_card.id,
        server.ManualCompletionInput(version=manual_card.version),
        user,
    ))
    assert_conflict(server.complete_card_from_manuals(
        manual_card.id,
        server.ManualCompletionInput(version=manual_card.version),
        user,
    ))
    assert asyncio.run(server.get_card(manual_card.id, user)).version == completed.version

    reference_card = asyncio.run(server.create_card(server.CardCreate(
        type="character", name="Riferimenti", reference_ids=[reference["id"]],
    ), user))
    refreshed = asyncio.run(server.refresh_card_reference_updates(
        reference_card.id,
        server.ReferenceUpdateInput(reference_ids=[reference["id"]], version=reference_card.version),
        user,
    ))
    assert_conflict(server.refresh_card_reference_updates(
        reference_card.id,
        server.ReferenceUpdateInput(reference_ids=[reference["id"]], version=reference_card.version),
        user,
    ))
    assert asyncio.run(server.get_card(reference_card.id, user)).version == refreshed["card"].version

    undo_card = asyncio.run(server.create_card(server.CardCreate(type="character", name="Cronologia"), user))
    changed = asyncio.run(server.update_card(
        undo_card.id,
        server.CardUpdate(attributes={"pf_attuali": "12"}, version=undo_card.version),
        user,
    ))
    changed_again = asyncio.run(server.update_card(
        undo_card.id,
        server.CardUpdate(attributes={"pf_attuali": "8"}, version=changed.version),
        user,
    ))
    assert_conflict(server.undo_card_change(
        undo_card.id,
        server.CardVersionInput(version=changed.version),
        user,
    ))
    assert asyncio.run(server.get_card(undo_card.id, user)).version == changed_again.version

    redo_card = asyncio.run(server.create_card(server.CardCreate(type="character", name="Ripristino"), user))
    changed_for_redo = asyncio.run(server.update_card(
        redo_card.id,
        server.CardUpdate(attributes={"pf_attuali": "12"}, version=redo_card.version),
        user,
    ))
    undone_for_redo = asyncio.run(server.undo_card_change(
        redo_card.id,
        server.CardVersionInput(version=changed_for_redo.version),
        user,
    ))
    refreshed_for_redo = asyncio.run(server.refresh_card_reference_updates(
        redo_card.id,
        server.ReferenceUpdateInput(version=undone_for_redo["card"].version),
        user,
    ))
    assert_conflict(server.redo_card_change(
        redo_card.id,
        server.CardVersionInput(version=undone_for_redo["card"].version),
        user,
    ))
    assert asyncio.run(server.get_card(redo_card.id, user)).version == refreshed_for_redo["card"].version

    linked_character = asyncio.run(server.create_card(server.CardCreate(
        type="character", name="Carte collegate", reference_ids=[reference["id"]],
    ), user))
    linked = asyncio.run(server.create_linked_cards(
        linked_character.id,
        server.LinkedCardInput(reference_ids=[reference["id"]], version=linked_character.version),
        user,
    ))
    assert len(linked) == 1
    assert_conflict(server.create_linked_cards(
        linked_character.id,
        server.LinkedCardInput(reference_ids=[reference["id"]], version=linked_character.version),
        user,
    ))
    assert len(cards.rows) == 6

    delete_card = asyncio.run(server.create_card(server.CardCreate(type="character", name="Da eliminare"), user))
    updated_for_delete = asyncio.run(server.update_card(
        delete_card.id,
        server.CardUpdate(name="Ancora qui", version=delete_card.version),
        user,
    ))
    assert_conflict(server.delete_card(
        delete_card.id,
        server.CardVersionInput(version=delete_card.version),
        user,
    ))
    assert asyncio.run(server.get_card(delete_card.id, user)).name == "Ancora qui"
    assert asyncio.run(server.delete_card(
        delete_card.id,
        server.CardVersionInput(version=updated_for_delete.version),
        user,
    )) == {"ok": True}


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
        server.ReferenceUpdateInput(reference_ids=[record["id"]], version=0),
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
        server.ReferenceUpdateInput(reference_ids=[original["id"]], version=character.version),
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
            server.LinkedCardInput(reference_ids=[record["id"]], version=character.version),
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


def test_translation_review_shows_private_comparison_and_unlocks_only_after_confirmation(monkeypatch):
    record = make_reference(
        "Barbaro",
        reference_type="class",
        source_language="es",
        source_name="Bárbaro",
        source_description="Un guerrero feroz.",
        source_full_text="Un guerrero feroz que combate con furia.",
        source_attributes={"dado_vita": "d12"},
        description="Un guerriero feroce.",
        full_text="Un guerriero feroce che combatte con furia.",
        attributes={"dado_vita": "d12"},
        source_refs=[{"filename": "Manual del Jugador.pdf", "page": 46, "language": "es"}],
        translation_status="translated",
        review_status="pending",
    )
    collection = MutableMemoryReferences([record])
    review_history = server.MemoryCollection()
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(
            private_reference_records=collection,
            private_reference_review_history=review_history,
        ),
    )
    owner = server.User(
        user_id="owner-1",
        email="mago@example.com",
        name="Mago",
        premium_manual=True,
    )
    other_user = server.User(
        user_id="owner-2",
        email="other@example.com",
        name="Other",
        premium_manual=True,
    )

    with pytest.raises(server.HTTPException, match="dato certo"):
        asyncio.run(server.apply_private_reference(record["id"], owner))

    details = asyncio.run(server.get_private_reference_review(record["id"], owner))
    assert details["original"]["name"] == "Bárbaro"
    assert details["original"]["full_text"] == "Un guerrero feroz que combate con furia."
    assert details["translation"]["name"] == "Barbaro"
    assert details["translation"]["full_text"] == "Un guerriero feroce che combatte con furia."
    assert details["manual"] == [{"filename": "Manual del Jugador.pdf", "page": 46, "language": "es"}]

    with pytest.raises(server.HTTPException) as other_owner:
        asyncio.run(server.get_private_reference_review(record["id"], other_user))
    assert other_owner.value.status_code == 404

    rejected = asyncio.run(server.review_private_reference(
        record["id"],
        server.ReferenceReviewInput(
            review_status="needs_review",
            review_notes="Controllare il termine tecnico nella seconda frase.",
        ),
        owner,
    ))
    assert rejected["needs_review"] is True
    assert rejected["review_notes"].startswith("Controllare")
    assert rejected["review_history"][0]["reviewer_id"] == owner.user_id
    assert rejected["review_history"][0]["reviewer_name"] == owner.name
    assert rejected["review_history"][0]["review_status"] == "needs_review"
    assert rejected["review_history"][0]["review_notes"] == "Controllare il termine tecnico nella seconda frase."
    assert rejected["review_history"][0]["reviewed_at"]
    with pytest.raises(server.HTTPException, match="dato certo"):
        asyncio.run(server.apply_private_reference(record["id"], owner))

    approved = asyncio.run(server.review_private_reference(
        record["id"],
        server.ReferenceReviewInput(
            review_status="verified",
            review_notes="Confrontata con il manuale alla pagina indicata.",
        ),
        owner,
    ))
    assert approved["is_trusted"] is True
    assert approved["review_status"] == "verified"
    assert approved["review_notes"].startswith("Confrontata")
    assert len(approved["review_history"]) == 2
    assert approved["review_history"][0]["review_status"] == "verified"
    assert approved["review_history"][1]["review_status"] == "needs_review"
    assert approved["review_history"][1]["review_notes"].startswith("Controllare")
    assert len(review_history.rows) == 2
    assert asyncio.run(server.apply_private_reference(record["id"], owner))["name"] == "Barbaro"


def test_concurrent_translation_reviews_append_every_decision(monkeypatch):
    class BarrierReferences(MutableMemoryReferences):
        def __init__(self, rows):
            super().__init__(rows)
            self.initial_readers = 0
            self.read_barrier = asyncio.Event()

        async def find_one(self, query):
            if self.initial_readers < 2:
                snapshot = await super().find_one(query)
                self.initial_readers += 1
                if self.initial_readers == 2:
                    self.read_barrier.set()
                await self.read_barrier.wait()
                return snapshot
            return await super().find_one(query)

    record = make_reference(
        "Barbaro",
        reference_type="class",
        source_language="es",
        translation_status="translated",
    )
    references = BarrierReferences([record])
    review_history = server.MemoryCollection()
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(
            private_reference_records=references,
            private_reference_review_history=review_history,
        ),
    )
    owner = server.User(
        user_id="owner-1",
        email="mago@example.com",
        name="Mago",
        premium_manual=True,
    )

    async def submit(status, notes):
        return await server.review_private_reference(
            record["id"],
            server.ReferenceReviewInput(review_status=status, review_notes=notes),
            owner,
        )

    async def submit_together():
        await asyncio.gather(
            submit("needs_review", "Controllare il nome."),
            submit("verified", "Confrontata riga per riga."),
        )

    asyncio.run(submit_together())

    details = asyncio.run(server.get_private_reference_review(record["id"], owner))
    assert {entry["review_status"] for entry in details["review_history"]} == {"needs_review", "verified"}
    assert {entry["review_notes"] for entry in details["review_history"]} == {
        "Controllare il nome.",
        "Confrontata riga per riga.",
    }


def test_verifying_a_record_clears_its_translation_error(monkeypatch):
    """review_private_reference must clear translation_error when status becomes 'verified'."""
    record = make_reference(
        "Barbaro",
        reference_type="class",
        source_language="es",
        translation_status="translated",
        translation_error="provider_rate_limited",
        review_status="pending",
    )
    collection = MutableMemoryReferences([record])
    review_history = server.MemoryCollection()
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(
            private_reference_records=collection,
            private_reference_review_history=review_history,
        ),
    )
    owner = server.User(user_id="owner-1", email="mago@example.com", name="Mago", premium_manual=True)

    asyncio.run(server.review_private_reference(
        record["id"],
        server.ReferenceReviewInput(review_status="verified", review_notes=""),
        owner,
    ))

    stored = collection.rows[0]
    assert stored["review_status"] == "verified"
    assert stored.get("translation_error", "") == ""


def test_needs_review_status_does_not_clear_translation_error(monkeypatch):
    """Only 'verified' should clear translation_error; 'needs_review' must leave it intact."""
    record = make_reference(
        "Barbaro",
        reference_type="class",
        source_language="es",
        translation_status="translated",
        translation_error="provider_rate_limited",
        review_status="pending",
    )
    collection = MutableMemoryReferences([record])
    review_history = server.MemoryCollection()
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(
            private_reference_records=collection,
            private_reference_review_history=review_history,
        ),
    )
    owner = server.User(user_id="owner-1", email="mago@example.com", name="Mago", premium_manual=True)

    asyncio.run(server.review_private_reference(
        record["id"],
        server.ReferenceReviewInput(review_status="needs_review", review_notes="Da ricontrollare."),
        owner,
    ))

    stored = collection.rows[0]
    assert stored["review_status"] == "needs_review"
    assert stored.get("translation_error") == "provider_rate_limited"


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
    assert captured["url"].endswith("/models/gemini-2.0-flash:generateContent")


def test_spanish_translation_uses_openai_only_after_gemini_failure(monkeypatch):
    calls = []

    class GeminiFailure:
        def raise_for_status(self):
            raise server.requests.HTTPError("429 Too Many Requests")

    class OpenAIResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": (
                            '{"records":[{"id":"ref-es","name":"Talento di guerra",'
                            '"description":"Un talento.","full_text":"Un talento completo.",'
                            '"attributes":{"prerequisito":"Forza 13"}}]}'
                        ),
                    },
                }],
            }

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return GeminiFailure() if "generativelanguage.googleapis.com" in url else OpenAIResponse()

    monkeypatch.setattr(server, "GEMINI_API_KEY", "gemini-test-key")
    monkeypatch.setattr(server, "OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setattr(server.requests, "post", fake_post)

    translated, error = server.translate_spanish_reference_batch([{
        "id": "ref-es",
        "source_name": "Talento de guerra",
        "source_description": "Un talento.",
        "source_full_text": "Un talento completo.",
        "source_attributes": {"prerequisito": "Fuerza 13"},
    }])

    assert error == ""
    assert translated["ref-es"]["name"] == "Talento di guerra"
    assert [url for url, _kwargs in calls] == [
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        "https://api.openai.com/v1/chat/completions",
    ]
    assert "Un talento completo." in calls[1][1]["json"]["messages"][1]["content"]


def test_automatic_preload_marks_successful_translations_verified(monkeypatch, tmp_path):
    """Auto-preload (auto_accept=True) promotes successful translations to verified/valid."""
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    collection = MutableMemoryReferences([])
    record = make_reference(
        "Talento de guerra",
        source_language="es",
        source_refs=[{"filename": filename, "page": 335, "language": "es"}],
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[record], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(
        server,
        "translate_spanish_reference_batch",
        lambda batch: ({
            batch[0]["id"]: {
                "name": "Talento di guerra",
                "description": "Un talento.",
                "full_text": "Un talento completo tradotto.",
                "attributes": {},
            },
        }, ""),
    )

    asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            start_page=335,
            end_page=335,
            translation_processing_confirmed=True,
            auto_accept=True,
        ),
    ))

    stored = collection.rows[0]
    assert stored["translation_status"] == "translated"
    # Auto-accept preload must promote successful translations to verified so
    # the library verifier can find valid probes without manual human review.
    assert stored["review_status"] == "verified"
    assert reference_review_state(stored) == "valid"


def test_manual_import_keeps_translations_pending_review(monkeypatch, tmp_path):
    """Manual imports (auto_accept=False) keep translations in needs_review for human confirmation."""
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    collection = MutableMemoryReferences([])
    record = make_reference(
        "Talento de guerra",
        source_language="es",
        source_refs=[{"filename": filename, "page": 335, "language": "es"}],
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[record], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(
        server,
        "translate_spanish_reference_batch",
        lambda batch: ({
            batch[0]["id"]: {
                "name": "Talento di guerra",
                "description": "Un talento.",
                "full_text": "Un talento completo tradotto.",
                "attributes": {},
            },
        }, ""),
    )

    asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            start_page=335,
            end_page=335,
            translation_processing_confirmed=True,
            auto_accept=False,
        ),
    ))

    stored = collection.rows[0]
    assert stored["translation_status"] == "translated"
    # Manual import must keep translations in needs_review; a person must
    # explicitly verify them before they count as authoritative references.
    assert stored["review_status"] == "needs_review"
    assert reference_review_state(stored) == "review"


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


def test_translate_spanish_batch_returns_rate_limited_when_both_providers_return_429(monkeypatch):
    """HTTP 429 from both providers must yield 'provider_rate_limited', not 'provider_translation_failed'."""
    from requests import HTTPError

    class RateLimitedResponse:
        status_code = 429
        def raise_for_status(self):
            err = HTTPError("429 Too Many Requests")
            err.response = self
            raise err

    def fake_post(url, **kwargs):
        return RateLimitedResponse()

    monkeypatch.setattr(server, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(server, "OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(server.requests, "post", fake_post)

    translated, error = server.translate_spanish_reference_batch([{
        "id": "ref-es",
        "source_name": "Bárbaro",
        "source_description": "Un guerrero.",
        "source_full_text": "Texto completo.",
        "source_attributes": {},
    }])

    assert translated == {}
    assert error == "provider_rate_limited"


def test_translate_spanish_batch_rate_limited_when_gemini_429_and_openai_fails(monkeypatch):
    """Gemini 429 + any OpenAI failure → 'provider_rate_limited' (primary provider was rate-limited)."""
    from requests import HTTPError

    class Gemini429:
        status_code = 429
        def raise_for_status(self):
            err = HTTPError("429 Too Many Requests")
            err.response = self
            raise err

    class OpenAIGenericFailure:
        def raise_for_status(self):
            raise HTTPError("500 Internal Server Error")

    def fake_post(url, **kwargs):
        if "generativelanguage" in url:
            return Gemini429()
        return OpenAIGenericFailure()

    monkeypatch.setattr(server, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(server, "OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(server.requests, "post", fake_post)

    translated, error = server.translate_spanish_reference_batch([{
        "id": "ref-es",
        "source_name": "Bárbaro",
        "source_description": "Un guerrero.",
        "source_full_text": "Texto completo.",
        "source_attributes": {},
    }])

    assert translated == {}
    assert error == "provider_rate_limited"


def test_translate_spanish_batch_rate_limited_when_openai_429_after_gemini_fails(monkeypatch):
    """OpenAI 429 after a non-rate-limit Gemini failure → 'provider_rate_limited'."""
    from requests import HTTPError

    class GeminiGenericFailure:
        def raise_for_status(self):
            raise HTTPError("500 Internal Server Error")

    class OpenAI429:
        status_code = 429
        def raise_for_status(self):
            err = HTTPError("429 Too Many Requests")
            err.response = self
            raise err

    def fake_post(url, **kwargs):
        if "generativelanguage" in url:
            return GeminiGenericFailure()
        return OpenAI429()

    monkeypatch.setattr(server, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(server, "OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(server.requests, "post", fake_post)

    translated, error = server.translate_spanish_reference_batch([{
        "id": "ref-es",
        "source_name": "Bárbaro",
        "source_description": "Un guerrero.",
        "source_full_text": "Texto completo.",
        "source_attributes": {},
    }])

    assert translated == {}
    assert error == "provider_rate_limited"


def test_spanish_translation_rate_limit_saves_record_without_review_flag(monkeypatch, tmp_path):
    """A rate-limited import must NOT add traduzione_da_verificare; the record stays pending retry."""
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    collection = MutableMemoryReferences([])
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(
            records=[make_reference("Bárbaro", reference_type="class")], pages_read=1, pages_needing_ocr=[]
        ),
    )
    monkeypatch.setattr(
        server, "translate_spanish_reference_batch",
        lambda batch: ({}, "provider_rate_limited"),
    )

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=5,
        ),
    ))

    stored = collection.rows[0]
    # Rate-limited records must not be immediately sent to human review.
    assert stored["translation_status"] == "failed"
    assert stored["translation_error"] == "provider_rate_limited"
    assert "traduzione_da_verificare" not in stored.get("review_flags", [])
    # Report counter separates rate limits from permanent failures.
    assert result.sources[0]["translation_rate_limited"] == 1
    assert result.sources[0]["translation_failed"] == 0


def test_rate_limited_batch_retries_each_record_individually_and_saves_successes(monkeypatch, tmp_path):
    """When a multi-record batch is rate-limited, each record is retried alone.

    Records the provider can handle individually are saved as 'translated';
    only those that are still limited stay as 'provider_rate_limited'.
    """
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    collection = MutableMemoryReferences([])
    barbaro = make_reference("Bárbaro", reference_type="class")
    ladron = make_reference("Ladrón", reference_type="class")
    barbaro_id = barbaro["id"]
    ladron_id = ladron["id"]

    # The batch (2 records) is rate-limited; individual retries: Bárbaro succeeds,
    # Ladrón is still rate-limited.  Use an ordered iterator so the mock is
    # independent of which record is retried first.
    responses = iter([
        ({}, "provider_rate_limited"),
        ({barbaro_id: {
            "name": "Barbaro",
            "description": "Un guerriero feroce.",
            "full_text": "Il barbaro combatte con rabbia selvaggia.",
            "attributes": {},
        }}, ""),
        ({}, "provider_rate_limited"),
    ])

    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(server, "translate_spanish_reference_batch", lambda batch: next(responses))

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=5,
        ),
    ))

    stored_by_source_name = {
        row["source_name"]: row for row in collection.rows
    }
    barbaro_row = stored_by_source_name["Bárbaro"]
    ladron_row = stored_by_source_name["Ladrón"]

    # The individually retried record that succeeded must be saved as translated.
    assert barbaro_row["translation_status"] == "translated", (
        "Bárbaro should be translated after its individual retry succeeded"
    )
    assert barbaro_row["name"] == "Barbaro"
    assert "traduzione_da_verificare" not in barbaro_row.get("review_flags", [])

    # The record still limited after its individual retry stays as rate-limited.
    assert ladron_row["translation_status"] == "failed"
    assert ladron_row["translation_error"] == "provider_rate_limited"
    assert "traduzione_da_verificare" not in ladron_row.get("review_flags", [])

    # Report must count each outcome separately.
    assert result.sources[0]["translated"] == 1
    assert result.sources[0]["translation_rate_limited"] == 1
    assert result.sources[0]["translation_failed"] == 0


def test_rate_limited_singleton_batch_is_not_retried_individually(monkeypatch, tmp_path):
    """A single-record batch that is rate-limited is not retried (no gain from splitting 1→1)."""
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    collection = MutableMemoryReferences([])
    barbaro = make_reference("Bárbaro", reference_type="class")

    call_count = [0]

    def mock_translate(batch):
        call_count[0] += 1
        return {}, "provider_rate_limited"

    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(server, "translate_spanish_reference_batch", mock_translate)

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=5,
        ),
    ))

    # Provider must be called exactly once — no individual-retry overhead for singletons.
    assert call_count[0] == 1, f"Expected 1 translate call, got {call_count[0]}"
    stored = collection.rows[0]
    assert stored["translation_status"] == "failed"
    assert stored["translation_error"] == "provider_rate_limited"
    assert result.sources[0]["translation_rate_limited"] == 1


def test_rate_limited_batch_individual_retry_content_error_marks_record_for_review(monkeypatch, tmp_path):
    """When an individual retry fails with a content error (not rate-limit), the record gets
    the traduzione_da_verificare review flag just like any other translation failure."""
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    collection = MutableMemoryReferences([])
    barbaro = make_reference("Bárbaro", reference_type="class")
    ladron = make_reference("Ladrón", reference_type="class")

    # Batch is rate-limited; Bárbaro individual retry has a content error;
    # Ladrón individual retry is still rate-limited.
    responses = iter([
        ({}, "provider_rate_limited"),
        ({}, "provider_translation_failed"),
        ({}, "provider_rate_limited"),
    ])

    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(server, "translate_spanish_reference_batch", lambda batch: next(responses))

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=5,
        ),
    ))

    stored_by_source_name = {
        row["source_name"]: row for row in collection.rows
    }
    barbaro_row = stored_by_source_name["Bárbaro"]
    ladron_row = stored_by_source_name["Ladrón"]

    # Content failure on individual retry → flagged for human review.
    assert barbaro_row["translation_status"] == "failed"
    assert barbaro_row["translation_error"] == "provider_translation_failed"
    assert "traduzione_da_verificare" in barbaro_row.get("review_flags", [])

    # Rate-limit on individual retry → no review flag, eligible for backoff retry.
    assert ladron_row["translation_status"] == "failed"
    assert ladron_row["translation_error"] == "provider_rate_limited"
    assert "traduzione_da_verificare" not in ladron_row.get("review_flags", [])

    assert result.sources[0]["translation_rate_limited"] == 1
    assert result.sources[0]["translation_failed"] == 1
    assert result.sources[0]["translated"] == 0


def test_rate_limited_batch_short_circuits_remaining_records_after_first_individual_429(monkeypatch, tmp_path):
    """When the first individual retry in a batch returns 429, remaining records must be
    marked provider_rate_limited directly — no extra API calls for them."""
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    collection = MutableMemoryReferences([])
    barbaro = make_reference("Bárbaro", reference_type="class")
    ladron = make_reference("Ladrón", reference_type="class")
    guerrero = make_reference("Guerrero", reference_type="class")

    call_count = [0]

    def mock_translate(batch):
        call_count[0] += 1
        if call_count[0] == 1:
            # Whole-batch call: rate-limited.
            return {}, "provider_rate_limited"
        # First individual retry (Bárbaro): still rate-limited → triggers short-circuit.
        return {}, "provider_rate_limited"

    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron, guerrero], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(server, "translate_spanish_reference_batch", mock_translate)

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            translation_batch_size=3,  # keep all 3 records in one batch
            start_page=5,
            end_page=5,
        ),
    ))

    # 1 batch call + 1 individual retry for Bárbaro → short-circuit, no calls for the other two.
    assert call_count[0] == 2, (
        f"Expected 2 translate calls (1 batch + 1 individual), got {call_count[0]}"
    )

    stored_by_source_name = {row["source_name"]: row for row in collection.rows}
    for name in ("Bárbaro", "Ladrón", "Guerrero"):
        row = stored_by_source_name[name]
        assert row["translation_status"] == "failed", f"{name} should be failed"
        assert row["translation_error"] == "provider_rate_limited", f"{name} should be provider_rate_limited"
        assert "traduzione_da_verificare" not in row.get("review_flags", []), (
            f"{name} should not have review flag"
        )

    assert result.sources[0]["translation_rate_limited"] == 3
    assert result.sources[0]["translated"] == 0
    assert result.sources[0]["translation_failed"] == 0


def test_subsequent_batches_skipped_when_provider_still_limited_after_individual_retry(monkeypatch, tmp_path):
    """When the individual-retry short-circuit confirms the provider is still rate-limiting,
    all remaining batches must be marked without any further provider calls."""
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    collection = MutableMemoryReferences([])
    # Three records that will end up in two batches of 1+2 via translation_batch_size=1.
    # Actually, to create 2 batches cleanly, use batch_size=2: first batch has 2 records,
    # second batch has 1 record.
    barbaro = make_reference("Bárbaro", reference_type="class")
    ladron = make_reference("Ladrón", reference_type="class")
    guerrero = make_reference("Guerrero", reference_type="class")

    call_count = [0]

    def mock_translate(batch):
        call_count[0] += 1
        if call_count[0] == 1:
            # First batch (Bárbaro + Ladrón): rate-limited.
            return {}, "provider_rate_limited"
        if call_count[0] == 2:
            # Individual retry for Bárbaro: still rate-limited → sets provider_exhausted.
            return {}, "provider_rate_limited"
        # Any further call would be an error — the second batch must be skipped.
        raise AssertionError(f"Unexpected translate call #{call_count[0]}")

    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron, guerrero], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(server, "translate_spanish_reference_batch", mock_translate)

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            translation_batch_size=2,  # batch 1: [Bárbaro, Ladrón], batch 2: [Guerrero]
            start_page=5,
            end_page=5,
        ),
    ))

    # 1 batch call + 1 individual retry for Bárbaro; Ladrón short-circuited within batch 1,
    # Guerrero's entire second batch skipped → only 2 calls total.
    assert call_count[0] == 2, (
        f"Expected 2 translate calls, got {call_count[0]}: "
        "batch 1 + 1 individual retry; batch 2 must be skipped entirely."
    )

    stored_by_source_name = {row["source_name"]: row for row in collection.rows}
    for name in ("Bárbaro", "Ladrón", "Guerrero"):
        row = stored_by_source_name[name]
        assert row["translation_status"] == "failed", f"{name} should be failed"
        assert row["translation_error"] == "provider_rate_limited", f"{name} should be provider_rate_limited"
        assert "traduzione_da_verificare" not in row.get("review_flags", []), (
            f"{name} should not have review flag"
        )

    assert result.sources[0]["translation_rate_limited"] == 3
    assert result.sources[0]["translated"] == 0
    assert result.sources[0]["translation_failed"] == 0


def test_subsequent_batches_skipped_when_singleton_batch_is_rate_limited(monkeypatch, tmp_path):
    """A rate-limited singleton batch (no individual retry possible) must set provider_exhausted
    so all subsequent batches are skipped without extra API calls."""
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    collection = MutableMemoryReferences([])
    barbaro = make_reference("Bárbaro", reference_type="class")
    ladron = make_reference("Ladrón", reference_type="class")

    call_count = [0]

    def mock_translate(batch):
        call_count[0] += 1
        if call_count[0] == 1:
            # First batch (singleton Bárbaro): rate-limited → provider_exhausted.
            return {}, "provider_rate_limited"
        raise AssertionError(f"Unexpected translate call #{call_count[0]} — second batch must be skipped")

    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=collection))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(
        server,
        "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(server, "translate_spanish_reference_batch", mock_translate)

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            translation_batch_size=1,  # force two singleton batches
            start_page=5,
            end_page=5,
        ),
    ))

    assert call_count[0] == 1, (
        f"Expected exactly 1 translate call, got {call_count[0]}: second singleton batch must be skipped."
    )

    stored_by_source_name = {row["source_name"]: row for row in collection.rows}
    for name in ("Bárbaro", "Ladrón"):
        row = stored_by_source_name[name]
        assert row["translation_status"] == "failed"
        assert row["translation_error"] == "provider_rate_limited"
        assert "traduzione_da_verificare" not in row.get("review_flags", [])

    assert result.sources[0]["translation_rate_limited"] == 2
    assert result.sources[0]["translated"] == 0


def test_rate_limit_retry_uses_backoff_delays_and_escalates_to_review_when_exhausted(monkeypatch):
    """_retry_rate_limited_translations retries each delay slot and adds the review flag when exhausted."""
    records = server.MemoryCollection()
    records.rows.append({
        "id": "ref-owned-barbaro",
        "user_id": "owner-1",
        "source_key": "manual.pdf",
        "translation_status": "failed",
        "translation_error": "provider_rate_limited",
        "review_flags": [],
        "review_status": "pending",
    })

    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    retry_calls: list[str] = []

    async def fake_retry(user_id, record_id):
        retry_calls.append(record_id)
        # Simulate continued rate-limiting by not changing the record's status.

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(server, "retry_private_reference_translation", fake_retry)

    remaining = asyncio.run(
        server._retry_rate_limited_translations(
            "owner-1", "manual.pdf", records,
            delays=(1, 2, 3),  # small test delays
        )
    )

    # All three delay slots must have been attempted.
    assert slept == [1, 2, 3]
    # The record must have been retried once per slot.
    assert retry_calls == ["ref-owned-barbaro", "ref-owned-barbaro", "ref-owned-barbaro"]
    # After exhausting retries the record must be escalated to human review.
    stored = records.rows[0]
    assert "traduzione_da_verificare" in stored.get("review_flags", [])
    assert stored["translation_error"] == "provider_rate_limited_exhausted"
    assert stored["review_status"] == "needs_review"
    assert remaining == 1


def test_rate_limit_retry_stops_early_when_record_succeeds(monkeypatch):
    """If a retry succeeds, subsequent delay slots are skipped."""
    records = server.MemoryCollection()
    records.rows.append({
        "id": "ref-owned-barbaro",
        "user_id": "owner-1",
        "source_key": "manual.pdf",
        "translation_status": "failed",
        "translation_error": "provider_rate_limited",
        "review_flags": [],
    })

    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    async def fake_retry(user_id, record_id):
        # Simulate success: clear the rate-limit error from the collection.
        for row in records.rows:
            if row["id"] == record_id:
                row["translation_error"] = ""
                row["translation_status"] = "translated"

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(server, "retry_private_reference_translation", fake_retry)

    remaining = asyncio.run(
        server._retry_rate_limited_translations(
            "owner-1", "manual.pdf", records,
            delays=(1, 2, 3),
        )
    )

    # Only the first delay slot should have been used.
    assert slept == [1]
    assert remaining == 0
    stored = records.rows[0]
    assert "traduzione_da_verificare" not in stored.get("review_flags", [])


def test_preload_worker_sets_rate_limit_status_and_triggers_retry(monkeypatch, tmp_path):
    """When import reports rate-limited records the worker sets last_error and triggers retry."""
    source = tmp_path / "Manuale.pdf"
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    records = server.MemoryCollection()
    records.rows.append({
        "id": "ref-owned-barbaro",
        "user_id": "owner-1",
        "source_key": source.name,
        "translation_status": "failed",
        "translation_error": "provider_rate_limited",
        "review_flags": [],
    })

    async def fake_import(_user_id, body):
        return server.ReferenceImportResult(
            imported=0, updated=0, flagged_for_review=0, skipped=0,
            sources=[{
                "filename": source.name,
                "pages_needing_ocr": [],
                "translation_rate_limited": 1,
            }],
        )

    retry_calls: list[str] = []

    async def fake_retry_rate_limited(user_id, filename, collection, delays=None, job_updater=None):
        retry_calls.append(filename)
        return 0

    monkeypatch.setattr(server, "db", SimpleNamespace(
        private_manual_import_jobs=jobs,
        private_reference_records=records,
    ))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(server, "manual_page_count", lambda _path: 1)
    monkeypatch.setattr(server, "import_private_reference_manuals", fake_import)
    monkeypatch.setattr(server, "_retry_rate_limited_translations", fake_retry_rate_limited)

    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput()))
    asyncio.run(server.run_manual_preload_worker("owner-1"))

    assert retry_calls == [source.name]
    job = jobs.rows[0]
    # Job must complete normally after the retry function returns.
    assert job["status"] == "completed"

def test_retry_rate_limited_calls_job_updater_before_each_sleep(monkeypatch):
    """_retry_rate_limited_translations must call job_updater with (attempt, retry_at) before sleeping."""
    records = server.MemoryCollection()
    records.rows.append({
        "id": "ref-owned-barbaro",
        "user_id": "owner-1",
        "source_key": "manual.pdf",
        "translation_status": "failed",
        "translation_error": "provider_rate_limited",
        "review_flags": [],
        "review_status": "pending",
    })

    slept: list[float] = []
    updater_calls: list[tuple] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    async def fake_retry(user_id, record_id):
        pass  # Keep record rate-limited to exercise all delay slots.

    async def fake_updater(attempt: int, retry_at: str) -> None:
        # retry_at must be an ISO timestamp and updater must fire BEFORE the sleep.
        updater_calls.append((attempt, retry_at, len(slept)))

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(server, "retry_private_reference_translation", fake_retry)

    asyncio.run(
        server._retry_rate_limited_translations(
            "owner-1", "manual.pdf", records,
            delays=(10, 20),
            job_updater=fake_updater,
        )
    )

    # Updater must be called once per delay slot, before the corresponding sleep.
    assert len(updater_calls) == 2
    assert updater_calls[0][0] == 0  # attempt index 0
    assert updater_calls[0][2] == 0  # fired before first sleep
    assert updater_calls[1][0] == 1  # attempt index 1
    assert updater_calls[1][2] == 1  # fired before second sleep (after first sleep)
    # retry_at must be a non-empty ISO string.
    for _attempt, retry_at, _sleep_count in updater_calls:
        assert "T" in retry_at, f"retry_at not an ISO timestamp: {retry_at!r}"
def test_rate_limit_retry_processes_all_records_beyond_page_boundary(monkeypatch):
    """_retry_rate_limited_translations must process every record, even when the
    total exceeds one drain page (>200) and storage order is not sequential.

    The stable id-sorted pagination must avoid gaps or duplicates regardless of
    insertion order — this catches the case where an unsorted SQL/PostgREST
    page boundary would skip rows between fetches.
    """
    # Create 600 rate-limited records inserted in REVERSE id order to ensure
    # that storage order != sorted order, exposing any sort-stability bug.
    records = server.MemoryCollection()
    for i in range(599, -1, -1):  # inserted as ref-0599 … ref-0000
        records.rows.append({
            "id": f"ref-{i:04d}",
            "user_id": "owner-1",
            "source_key": "manual.pdf",
            "translation_status": "failed",
            "translation_error": "provider_rate_limited",
            "review_flags": [],
            "review_status": "pending",
        })

    retried: list[str] = []

    async def fake_sleep(_s):
        pass

    async def fake_retry(user_id, record_id):
        retried.append(record_id)
        # All retries keep failing with rate-limit to exercise exhaustion path.

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(server, "retry_private_reference_translation", fake_retry)

    remaining = asyncio.run(
        server._retry_rate_limited_translations(
            "owner-1", "manual.pdf", records, delays=(1,)
        )
    )

    # Every record must have been retried exactly once.
    assert len(retried) == 600, f"Only {len(retried)} of 600 records were retried"
    assert len(set(retried)) == 600, "Duplicate retries detected"
    # Retries must have been issued in stable id-sorted order (not insertion order).
    assert retried == sorted(retried), "Retries were not in stable id-sorted order"
    # Every record must be escalated to human review after exhaustion.
    still_parked = [
        r for r in records.rows if r.get("translation_error") == "provider_rate_limited"
    ]
    assert still_parked == [], f"{len(still_parked)} records remain silently rate-limited"
    assert remaining == 600
    # All must carry the review flag.
    for row in records.rows:
        assert "traduzione_da_verificare" in row.get("review_flags", [])


def test_repeated_429_during_backoff_never_adds_review_flag_before_exhaustion(monkeypatch):
    """Each 429 during backoff retries must leave traduzione_da_verificare absent;
    only final exhaustion by _retry_rate_limited_translations may add it."""
    record = {
        **make_reference(
            "Bárbaro",
            reference_type="class",
            source_language="es",
            source_key="manual.pdf",
            source_name="Bárbaro",
            source_description="Un guerrero feroz.",
            source_full_text="Un guerrero feroz que combate con furia.",
            source_attributes={},
            translation_status="failed",
            translation_error="provider_rate_limited",
            review_flags=[],
            review_status="pending",
        ),
        "id": "ref-owned-barbaro",
    }
    records = server.MemoryCollection()
    records.rows.append(record.copy())

    # Provider always rate-limits — simulates the worst case.
    monkeypatch.setattr(
        server,
        "translate_spanish_reference_batch",
        lambda batch: ({}, "provider_rate_limited"),
    )

    slept: list[float] = []

    async def fake_sleep(s):
        slept.append(s)
        # After each sleep, verify the record still has NO review flag —
        # the backoff window must not escalate prematurely.
        stored = records.rows[0]
        assert "traduzione_da_verificare" not in stored.get("review_flags", []), (
            f"traduzione_da_verificare appeared prematurely after sleep {s}"
        )

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=records))

    remaining = asyncio.run(
        server._retry_rate_limited_translations(
            "owner-1", "manual.pdf", records, delays=(1, 2)
        )
    )

    # Both delay slots must have fired.
    assert slept == [1, 2]
    # After exhaustion the record must be escalated to human review.
    stored = records.rows[0]
    assert "traduzione_da_verificare" in stored.get("review_flags", [])
    assert stored["translation_error"] == "provider_rate_limited_exhausted"
    assert stored["review_status"] == "needs_review"
    assert remaining == 1


def test_retry_rate_limited_does_not_overwrite_user_verified_translation(monkeypatch):
    """_retry_rate_limited_translations must not touch records the user has verified.

    Scenario: the provider rate-limits a record, but before the automatic
    backoff loop can retry it the user manually reviews and verifies the
    translation.  The retry loop must skip both the provider call and the
    exhaustion escalation so the human decision survives the recovery cycle.
    """
    verified_name = "Barbaro (verificato dall'utente)"
    verified_description = "Descrizione verificata manualmente."
    record = make_reference(
        "Bárbaro",
        reference_type="class",
        source_language="es",
        source_key="manual.pdf",
        source_name="Bárbaro",
        source_description="Un guerrero feroz.",
        source_full_text="Un guerrero feroz que combate con furia.",
        source_attributes={},
        translation_status="failed",
        translation_error="provider_rate_limited",
        review_status="verified",
        review_flags=[],
    )
    # Simulate content that was set when the user verified the record.
    record["id"] = "ref-owned-barbaro"
    record["name"] = verified_name
    record["description"] = verified_description
    records = server.MemoryCollection()
    records.rows.append(record.copy())

    translate_calls: list = []
    monkeypatch.setattr(
        server,
        "translate_spanish_reference_batch",
        lambda batch: (translate_calls.append(batch) or ({}, "")),
    )

    async def fake_sleep(_s):
        pass

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=records))

    remaining = asyncio.run(
        server._retry_rate_limited_translations(
            "owner-1", "manual.pdf", records, delays=(0,)
        )
    )

    # The translation provider must not have been contacted for a verified record.
    assert translate_calls == [], "translate_spanish_reference_batch was called for a verified record"
    # The user-verified content must survive the backoff cycle unchanged.
    stored = records.rows[0]
    assert stored["review_status"] == "verified", "User verification was overwritten"
    assert stored["name"] == verified_name, "Verified translation name was overwritten"
    assert stored["description"] == verified_description, "Verified description was overwritten"
    # The record must not be escalated to needs_review by the exhaustion path.
    assert "traduzione_da_verificare" not in stored.get("review_flags", []), (
        "Exhaustion path added review flag to a user-verified record"
    )
    # The return value reflects records still carrying the rate-limit error.
    # The verified record is not escalated but still counts as unresolved from
    # the system's perspective — the important guarantee is content preservation.
    assert isinstance(remaining, int)


def test_retry_translation_finalization_skips_record_verified_during_provider_call(monkeypatch):
    """retry_private_reference_translation must not overwrite a verification that
    races the provider call.

    Scenario:
    1. Record has translation_status='failed' and review_status='pending'.
    2. retry_private_reference_translation claims it (sets status=processing).
    3. While the provider call is in flight the user verifies the record —
       review_status becomes 'verified' and the name is set to the approved
       value; the processing status and lease_id are left untouched by the
       user action.
    4. The provider returns a translation result.
    5. The finalization update predicate includes review_status != 'verified',
       so it matches zero rows and the user-verified content is preserved.
    """
    user_verified_name = "Barbaro (approvato dall'utente)"
    provider_name = "Barbaro (traduzione automatica)"

    record = {
        **make_reference(
            "Bárbaro",
            reference_type="class",
            source_language="es",
            source_key="manual.pdf",
            source_name="Bárbaro",
            source_description="Un guerrero feroz.",
            source_full_text="Un guerrero feroz que combate con furia.",
            source_attributes={},
            translation_status="failed",
            translation_error="provider_rate_limited",
            review_status="pending",
            review_flags=[],
        ),
        "id": "ref-owned-barbaro",
    }
    records = server.MemoryCollection()
    records.rows.append(record.copy())

    def translate_and_verify(batch):
        # Simulate the user verifying the record while the provider is working.
        # Only review_status and name are updated — the pipeline fields
        # (translation_status=processing, lease_id) remain as the claim set them
        # because the user action does not touch the processing pipeline.
        for row in records.rows:
            if row["id"] == batch[0]["id"]:
                row["review_status"] = "verified"
                row["name"] = user_verified_name
        return {
            batch[0]["id"]: {
                "name": provider_name,
                "description": "Traduzione automatica.",
                "full_text": "Testo tradotto automaticamente.",
                "attributes": {},
            }
        }, ""

    monkeypatch.setattr(server, "translate_spanish_reference_batch", translate_and_verify)
    monkeypatch.setattr(server, "db", SimpleNamespace(private_reference_records=records))

    asyncio.run(server.retry_private_reference_translation("owner-1", "ref-owned-barbaro"))

    stored = records.rows[0]
    assert stored["review_status"] == "verified", (
        "Concurrent user verification was overwritten by the retry finalization"
    )
    assert stored["name"] == user_verified_name, (
        f"Provider result overwrote verified name; got {stored['name']!r}"
    )


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


def test_manual_import_progress_reports_pages_translation_and_review_states():
    records = [
        make_reference(
            "Barbaro",
            reference_type="class",
            source_language="es",
            source_refs=[{"filename": "Manual del Jugador.pdf", "page": 5, "language": "es"}],
            translation_status="translated",
        ),
        make_reference(
            "Guerrero",
            reference_type="class",
            source_language="es",
            source_refs=[{"filename": "Manual del Jugador.pdf", "page": 6, "language": "es"}],
            translation_status="failed",
            review_flags=["traduzione_da_verificare"],
            review_status="needs_review",
        ),
    ]

    progress = server.manual_import_progress("Manual del Jugador.pdf", records, 10)

    assert progress["records_total"] == 2
    assert progress["records_translated"] == 1
    assert progress["records_failed"] == 1
    assert progress["records_to_review"] == 2
    assert progress["records_ready"] == 0
    assert progress["pages_with_records"] == 2
    assert progress["imported_pages"] == [5, 6]
    assert progress["translation_progress"] == 50
    assert progress["page_progress"] == 20


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


def test_automatic_preload_queues_translation_and_ocr_without_user_consent(monkeypatch, tmp_path):
    native = tmp_path / "Manuale-nativo.pdf"
    spanish = tmp_path / "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    scanned = tmp_path / "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf"
    for source in (native, spanish, scanned):
        source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(private_manual_import_jobs=jobs),
    )
    monkeypatch.setattr(
        server,
        "available_reference_manuals",
        lambda: {
            native.name: native,
            spanish.name: spanish,
            scanned.name: scanned,
        },
    )
    monkeypatch.setattr(server, "manual_page_count", lambda _path: 8)

    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput()))
    by_filename = {job["filename"]: job for job in jobs.rows}
    assert by_filename[native.name]["status"] == "queued"
    assert by_filename[spanish.name]["status"] == "queued"
    assert by_filename[spanish.name]["translation_processing_confirmed"] is True
    assert by_filename[scanned.name]["status"] == "queued"
    assert by_filename[scanned.name]["external_processing_confirmed"] is True


def test_automatic_preload_can_queue_only_the_requested_manual(monkeypatch, tmp_path):
    spanish = tmp_path / "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    other = tmp_path / "Manuale-Altro.pdf"
    spanish.write_bytes(b"manual")
    other.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(private_manual_import_jobs=jobs))
    monkeypatch.setattr(
        server,
        "available_reference_manuals",
        lambda: {spanish.name: spanish, other.name: other},
    )
    monkeypatch.setattr(server, "manual_page_count", lambda _path: 1018)

    asyncio.run(server.ensure_manual_preload_jobs(
        "owner-1",
        server.ManualPreloadInput(filename=spanish.name),
    ))

    assert [job["filename"] for job in jobs.rows] == [spanish.name]
    assert jobs.rows[0]["translation_processing_confirmed"] is True


def test_automatic_preload_processes_all_chunks_without_manual_ranges(monkeypatch, tmp_path):
    source = tmp_path / "Manuale-nativo.pdf"
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    calls = []
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(private_manual_import_jobs=jobs),
    )
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(server, "manual_page_count", lambda _path: 25)

    async def fake_import(owner_id, body):
        calls.append((owner_id, body.start_page, body.end_page, body.use_ai_ocr, body.auto_accept))
        return server.ReferenceImportResult(
            imported=2,
            updated=1,
            flagged_for_review=1,
            skipped=0,
            sources=[{"filename": source.name, "pages_needing_ocr": []}],
        )

    monkeypatch.setattr(server, "import_private_reference_manuals", fake_import)
    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput()))
    asyncio.run(server.run_manual_preload_worker("owner-1"))

    job = jobs.rows[0]
    assert calls == [
        ("owner-1", 1, 12, False, True),
        ("owner-1", 13, 24, False, True),
        ("owner-1", 25, 25, False, True),
    ]
    assert job["status"] == "completed"
    assert job["current_page"] == 26
    assert job["records_imported"] == 6
    assert job["records_updated"] == 3
    assert job["records_flagged"] == 3


def test_automatic_preload_starts_ocr_without_user_consent(monkeypatch, tmp_path):
    source = tmp_path / "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf"
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    calls = []
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(private_manual_import_jobs=jobs),
    )
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(server, "manual_page_count", lambda _path: 6)

    async def fake_import(_owner_id, body):
        calls.append((body.use_ai_ocr, body.external_processing_confirmed, body.auto_accept))
        return server.ReferenceImportResult(
            imported=1,
            updated=0,
            flagged_for_review=1,
            skipped=0,
            sources=[{"filename": source.name, "pages_needing_ocr": []}],
        )

    monkeypatch.setattr(server, "import_private_reference_manuals", fake_import)
    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput()))
    asyncio.run(server.run_manual_preload_worker("owner-1"))

    assert jobs.rows[0]["status"] == "completed"
    assert calls == [(True, True, True)]


def test_spanish_preload_skips_unreadable_cover_pages_and_continues(monkeypatch, tmp_path):
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    source = tmp_path / filename
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(private_manual_import_jobs=jobs))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(server, "manual_page_count", lambda _path: 2)

    calls = []

    async def fake_import(_user_id, body):
        calls.append(body.use_ai_ocr)
        return server.ReferenceImportResult(
            imported=0, updated=0, flagged_for_review=0, skipped=0,
            sources=[{"filename": filename, "pages_needing_ocr": [1]}],
        )

    monkeypatch.setattr(server, "import_private_reference_manuals", fake_import)
    asyncio.run(server.ensure_manual_preload_jobs(
        "owner-1",
        server.ManualPreloadInput(filename=filename),
    ))
    asyncio.run(server.run_manual_preload_worker("owner-1"))

    assert jobs.rows[0]["status"] == "completed"
    assert jobs.rows[0]["current_page"] == 3
    assert jobs.rows[0]["pages_needing_ocr"] == [1]
    assert calls == [False]


def test_preload_checkpoint_ignores_a_worker_that_lost_its_lease(monkeypatch, tmp_path):
    source = tmp_path / "Manuale-nativo.pdf"
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(private_manual_import_jobs=jobs))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(server, "manual_page_count", lambda _path: 2)

    async def fake_import(*_args, **_kwargs):
        return server.ReferenceImportResult(
            imported=1, updated=0, flagged_for_review=0, skipped=0,
            sources=[{"filename": source.name, "pages_needing_ocr": []}],
        )

    monkeypatch.setattr(server, "import_private_reference_manuals", fake_import)
    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput()))
    claimed = asyncio.run(server.claim_next_manual_preload_job("owner-1"))
    assert claimed and claimed["lease_id"]

    jobs.rows[0]["lease_id"] = "new-owner-lease"
    asyncio.run(server.process_manual_preload_job("owner-1", claimed))

    assert jobs.rows[0]["status"] == "processing"
    assert jobs.rows[0]["lease_id"] == "new-owner-lease"
    assert jobs.rows[0]["current_page"] == 1
    assert jobs.rows[0]["records_imported"] == 0


def test_startup_reclaims_only_expired_preload_leases(monkeypatch):
    now = int(time.time())
    jobs = server.MemoryCollection()
    jobs.rows.extend([
        {
            "id": "expired", "user_id": "owner-1", "status": "processing",
            "lease_expires_at": now - 1, "updated_at": server.utc_now(),
        },
        {
            "id": "active", "user_id": "owner-2", "status": "processing",
            "lease_expires_at": now + 600, "updated_at": server.utc_now(),
        },
    ])
    monkeypatch.setattr(server, "db", SimpleNamespace(private_manual_import_jobs=jobs))
    started = []
    monkeypatch.setattr(server, "start_manual_preload_worker", lambda user_id: started.append(user_id))

    asyncio.run(server.resume_manual_preload_workers())

    assert jobs.rows[0]["status"] == "queued"
    assert jobs.rows[1]["status"] == "processing"
    assert started == ["owner-1"]


def test_startup_requeues_completed_manual_when_its_parser_revision_changes(monkeypatch, tmp_path):
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    source = tmp_path / filename
    source.write_bytes(b"native-text")
    jobs = server.MemoryCollection()
    jobs.rows.append({
        "id": "completed-spanish-manual",
        "user_id": "owner-1",
        "filename": filename,
        "status": "completed",
        "source_fingerprint": "previous-parser-revision",
        "current_page": 1018,
        "records_imported": 803,
    })
    monkeypatch.setattr(server, "db", SimpleNamespace(private_manual_import_jobs=jobs))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(server, "manual_page_count", lambda _path: 1018)
    started = []
    monkeypatch.setattr(server, "start_manual_preload_worker", lambda user_id: started.append(user_id))

    asyncio.run(server.resume_manual_preload_workers())

    assert jobs.rows[0]["status"] == "queued"
    assert jobs.rows[0]["current_page"] == 1
    assert jobs.rows[0]["source_fingerprint"] == server.manual_source_fingerprint(source)
    assert started == ["owner-1"]


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

def test_manual_preload_summary_exposes_translation_retry_fields():
    """manual_preload_summary must include translation_retry_at and translation_retry_attempt."""
    # no-job case: fields must default to None / 0.
    summary = server.manual_preload_summary(None, 10)
    assert summary["translation_retry_at"] is None
    assert summary["translation_retry_attempt"] == 0

    # job without retry info: fields must still default safely.
    job_no_retry = {
        "status": "processing",
        "current_page": 2,
        "page_count": 5,
        "records_imported": 10,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "pages_needing_ocr": [],
        "last_error": "translation_rate_limited",
        "translation_processing_confirmed": True,
        "external_processing_confirmed": False,
    }
    summary_no_retry = server.manual_preload_summary(job_no_retry, 5)
    assert summary_no_retry["translation_retry_at"] is None
    assert summary_no_retry["translation_retry_attempt"] == 0

    # job with retry info: fields must be propagated.
    retry_ts = "2026-08-23T12:00:30+00:00"
    job_with_retry = {
        **job_no_retry,
        "translation_retry_at": retry_ts,
        "translation_retry_attempt": 2,
    }
    summary_with_retry = server.manual_preload_summary(job_with_retry, 5)
    assert summary_with_retry["translation_retry_at"] == retry_ts
    assert summary_with_retry["translation_retry_attempt"] == 2

def test_preload_worker_writes_retry_state_to_job(monkeypatch, tmp_path):
    """process_manual_preload_job must write translation_retry_at/attempt to the job
    before each backoff sleep so the summary endpoint can expose them."""
    source = tmp_path / "Manuale.pdf"
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    records = server.MemoryCollection()
    records.rows.append({
        "id": "ref-owned-barbaro",
        "user_id": "owner-1",
        "source_key": source.name,
        "translation_status": "failed",
        "translation_error": "provider_rate_limited",
        "review_flags": [],
    })

    async def fake_import(_user_id, body):
        return server.ReferenceImportResult(
            imported=0, updated=0, flagged_for_review=0, skipped=0,
            sources=[{
                "filename": source.name,
                "pages_needing_ocr": [],
                "translation_rate_limited": 1,
            }],
        )

    updater_snapshots: list[dict] = []

    async def capturing_retry(user_id, filename, collection, delays=None, job_updater=None):
        # Call the updater once as the real function would (attempt 0).
        if job_updater is not None:
            await job_updater(0, "2026-08-23T12:00:30+00:00")
            # Capture the job state immediately after the updater fires.
            if jobs.rows:
                updater_snapshots.append(dict(jobs.rows[0]))
        return 0

    monkeypatch.setattr(server, "db", SimpleNamespace(
        private_manual_import_jobs=jobs,
        private_reference_records=records,
    ))
    monkeypatch.setattr(server, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(server, "manual_page_count", lambda _path: 1)
    monkeypatch.setattr(server, "import_private_reference_manuals", fake_import)
    monkeypatch.setattr(server, "_retry_rate_limited_translations", capturing_retry)

    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput()))
    asyncio.run(server.run_manual_preload_worker("owner-1"))

    assert updater_snapshots, "job_updater was never called"
    snap = updater_snapshots[0]
    assert snap.get("translation_retry_at") == "2026-08-23T12:00:30+00:00"
    assert snap.get("translation_retry_attempt") == 1  # attempt 0 → stored as 1

    # After the retry loop finishes, the stale backoff state must be cleared so
    # manual_preload_summary never shows a countdown for a completed retry cycle.
    final_job = jobs.rows[0]
    assert final_job.get("translation_retry_at") is None, (
        "translation_retry_at should be cleared after retry loop completes"
    )
    assert int(final_job.get("translation_retry_attempt") or 0) == 0, (
        "translation_retry_attempt should be reset to 0 after retry loop completes"
    )

def test_retry_rate_limited_without_job_updater_does_not_raise(monkeypatch):
    """Omitting job_updater (None) must work without errors."""
    records = server.MemoryCollection()
    records.rows.append({
        "id": "ref-owned-r",
        "user_id": "owner-1",
        "source_key": "manual.pdf",
        "translation_status": "failed",
        "translation_error": "provider_rate_limited",
        "review_flags": [],
        "review_status": "pending",
    })

    async def fake_sleep(_s):
        pass

    async def fake_retry(_uid, _rid):
        pass

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(server, "retry_private_reference_translation", fake_retry)

    # Must not raise even though job_updater is not provided.
    remaining = asyncio.run(
        server._retry_rate_limited_translations(
            "owner-1", "manual.pdf", records, delays=(1,)
        )
    )
    assert remaining == 1  # record still rate-limited → escalated
