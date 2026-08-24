import asyncio
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import server
import services.library as lib_mod
import services.preload as preload_mod
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
    import pymupdf as fitz
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
    import pymupdf as fitz
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
    import pymupdf as fitz
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
    import pymupdf as fitz
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
    import pymupdf as fitz
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
    monkeypatch.setattr(lib_mod, "GEMINI_API_KEY", "test-key")

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


def test_reference_search_does_not_match_a_different_name_with_shared_suffix():
    records = [
        make_reference("Lama di Fuoco", reference_type="spell"),
        make_reference("Foglia di Fuoco", reference_type="spell"),
    ]

    matches = search_reference_records(records, "lama di fuoco", reference_type="spell")

    assert [record["name"] for record in matches] == ["Lama di Fuoco"]


def test_spell_payload_derives_damage_and_card_action_from_imported_text():
    payload = reference_to_card_payload(make_reference(
        "Lama infuocata",
        reference_type="spell",
        attributes={
            "livello": "2",
            "scuola": "Evocazione",
            "tempo_lancio": "1 azione aggiuntiva",
            "gittata": "Lanciatore",
            "componenti": "V, S, M",
            "durata": "Concentrazione, fino a 10 minuti",
            "concentrazione": "Sì",
        },
        full_text=(
            "Evocazione livello 2. Tempo di lancio: 1 azione aggiuntiva. "
            "Se colpisci, l'obiettivo subisce 3d6 danni da fuoco."
        ),
    ))

    assert payload["attributes"]["azione"] == "1 azione aggiuntiva"
    assert payload["attributes"]["tempo_lancio"] == "1 azione aggiuntiva"
    assert payload["attributes"]["danno"] == "3d6 danni da fuoco"
    assert payload["story"] == payload["description"]


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


def test_verified_review_status_overrides_failed_translation_status():
    """A record manually verified by a human is trusted even when the automated
    translation failed — the reviewer has personally confirmed the content."""
    record = make_reference(
        "Guerriero",
        reference_type="class",
        source_language="es",
        source_name="Guerrero",
        translation_status="failed",
        review_status="verified",
    )

    assert reference_review_state(record) == "valid"
    assert reference_is_trusted(record)


def test_apply_reference_endpoint_accepts_verified_record_with_failed_translation(monkeypatch):
    """POST /library/{id}/apply must succeed for a record that has
    review_status='verified' and translation_status='failed'.
    The human verification overrides the translation failure."""
    record = make_reference(
        "Guerriero",
        reference_type="class",
        source_language="es",
        source_name="Guerrero",
        description="Un combattente marziale esperto.",
        translation_status="failed",
        review_status="verified",
    )
    # is_trusted must be True — the endpoint gate relies on it, not on translation_status
    assert reference_is_trusted(record), (
        "reference_is_trusted must return True when review_status='verified', "
        "even when translation_status='failed'"
    )
    _test_db = SimpleNamespace(private_reference_records=MemoryReferences([record]))

    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago")

    result = asyncio.run(server.apply_private_reference(record["id"], user, db=_test_db))

    assert result["name"] == "Guerriero"
    assert result["reference_id"] == record["id"]


def test_apply_reference_endpoint_rejects_unverified_record_with_failed_translation(monkeypatch):
    """POST /library/{id}/apply must return HTTP 409 when translation_status='failed'
    and the record has NOT been manually verified (review_status != 'verified').
    This proves the endpoint enforces the is_trusted gate, not a bypass of it."""
    record = make_reference(
        "Guerriero Non Verificato",
        reference_type="class",
        source_language="es",
        source_name="Guerrero",
        description="Un combattente marziale non ancora verificato.",
        translation_status="failed",
        review_status="pending",
    )
    # is_trusted must be False — a failed translation without human sign-off is blocked
    assert not reference_is_trusted(record), (
        "reference_is_trusted must return False when translation_status='failed' "
        "and review_status is not 'verified'"
    )
    _test_db = SimpleNamespace(private_reference_records=MemoryReferences([record]))

    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago")

    with pytest.raises(server.HTTPException, match="dato certo") as error:
        asyncio.run(server.apply_private_reference(record["id"], user, db=_test_db))

    assert error.value.status_code == 409


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
    _test_db = SimpleNamespace(cards=cards, private_reference_records=references)

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
    ), user, db=_test_db))
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
        user, db=_test_db))
    assert len(linked) == 1
    assert linked[0].reference_ids == [record["id"]]
    assert linked[0].source_refs == record["source_refs"]
    assert linked[0].rule_sources[0]["name"] == record["name"]

    current_character = asyncio.run(server.get_card(character.id, user, db=_test_db))
    updated = asyncio.run(server.update_card(
        character.id,
        server.CardUpdate(reference_ids=[], version=current_character.version),
        user, db=_test_db))
    assert updated.source_refs == []
    assert updated.rule_sources == []
    assert updated.attributes["privilegi"] == [{"nome": "Scelta manuale"}]
    restored = asyncio.run(server.undo_card_change(
        character.id,
        server.CardVersionInput(version=updated.version),
        user, db=_test_db))
    assert restored["card"].reference_ids == [record["id"]]
    assert restored["card"].rule_sources[0]["source_id"] == record["id"]
    snapshot = restored["entry"]["before"]["reference_snapshots"][0]
    assert "description" not in snapshot
    assert "full_text" not in snapshot

    try:
        asyncio.run(server.create_linked_cards(
            character.id,
            server.LinkedCardInput(reference_ids=["ref-non-collegato"], version=updated.version),
            user, db=_test_db))
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
    _test_db = SimpleNamespace(cards=cards, private_reference_records=references)

    user = server.User(user_id="owner-1", email="ranger@example.com", name="Ranger")
    character = asyncio.run(server.create_card(server.CardCreate(
        type="character",
        name="Artemis",
        reference_ids=[first["id"], second["id"]],
    ), user, db=_test_db))

    with pytest.raises(RuntimeError, match="Errore di persistenza"):
        asyncio.run(server.create_linked_cards(
            character.id,
            server.LinkedCardInput(
                reference_ids=[first["id"], second["id"]],
                version=character.version,
            ),
            user, db=_test_db))

    assert [card for card in cards.rows if card["type"] != "character"] == []
    restored_character = asyncio.run(server.get_card(character.id, user, db=_test_db))
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
    _test_db = SimpleNamespace(cards=cards, private_reference_records=references)

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
    ), user, db=_test_db))
    saved_snapshot = character.reference_snapshots[0]
    assert saved_snapshot["source_text_checksum"] == "versione-originale"
    assert reference_snapshot_changed(saved_snapshot, corrected)
    assert reference_snapshot(corrected)["content_revision"] != saved_snapshot["content_revision"]

    references.rows[0] = corrected
    report = asyncio.run(server.card_reference_updates(character.id, user, db=_test_db))
    assert report["updated_count"] == 1
    assert "full_text" not in report["updates"][0]["before"]
    assert "full_text" not in report["updates"][0]["after"]
    assert "testo" in report["updates"][0]["changed_fields"]

    refreshed = asyncio.run(server.refresh_card_reference_updates(
        character.id,
        server.ReferenceUpdateInput(reference_ids=[original["id"]], version=character.version),
        user, db=_test_db))
    assert refreshed["card"].attributes["dado_vita"] == "d12"
    assert refreshed["card"].attributes["tiri_salvezza"] == "Forza, Destrezza"
    assert "dado_vita" in refreshed["protected_fields"][original["id"]]
    assert refreshed["card"].reference_snapshots[0]["source_text_checksum"] == "versione-corretta"
    assert asyncio.run(server.card_reference_updates(character.id, user, db=_test_db))["updated_count"] == 0


def test_card_history_keeps_manual_and_user_changes_separate_and_account_scoped(monkeypatch):
    cards = server.MemoryCollection()
    reference = make_reference(
        "Guerriero",
        reference_type="class",
        attributes={"dado_vita": "d10", "tiri_salvezza": "Forza, Costituzione"},
    )
    references = server.MemoryCollection()
    references.rows.append(reference)
    _test_db = SimpleNamespace(cards=cards, private_reference_records=references)

    owner = server.User(user_id="owner-1", email="owner@example.com", name="Owner")
    other_user = server.User(user_id="owner-2", email="other@example.com", name="Other")

    character = asyncio.run(server.create_card(server.CardCreate(
        type="character",
        name="Neris",
        reference_ids=[reference["id"]],
        attributes={"classe": "Guerriero", "punti_ferita": "18", "dadi_vita": "d10"},
    ), owner, db=_test_db))
    user_saved = asyncio.run(server.update_card(
        character.id,
        server.CardUpdate(
            attributes={"classe": "Guerriero", "punti_ferita": "18", "dadi_vita": "d12", "pf_attuali": "14"},
            version=character.version,
        ),
        owner, db=_test_db))
    assert user_saved.change_history[-1]["source"] == "user"
    assert user_saved.change_history[-1]["changed_fields"] == ["attributes"]

    manual_saved = asyncio.run(server.complete_card_from_manuals(
        character.id,
        server.ManualCompletionInput(version=user_saved.version),
        owner, db=_test_db))
    assert manual_saved.change_history[-1]["source"] == "manual"
    assert manual_saved.change_history[-1]["action"] == "manual_completion"

    undone = asyncio.run(server.undo_card_change(
        character.id, server.CardVersionInput(version=manual_saved.version), owner, db=_test_db))
    assert undone["card"].attributes["dadi_vita"] == "d12"
    assert undone["card"].attributes["pf_attuali"] == "14"
    assert "tiri_salvezza" not in undone["card"].attributes
    assert undone["history"][-1]["undone"] is True

    redone = asyncio.run(server.redo_card_change(
        character.id, server.CardVersionInput(version=undone["card"].version), owner, db=_test_db))
    assert redone["card"].attributes["tiri_salvezza"] == "Forza, Costituzione"
    assert redone["card"].attributes["pf_attuali"] == "14"

    try:
        asyncio.run(server.card_history(character.id, other_user, db=_test_db))
        assert False, "Expected the other account not to access this card history"
    except server.HTTPException as error:
        assert error.status_code == 404


def test_card_history_redo_follows_undo_order_and_drops_stale_branches(monkeypatch):
    cards = server.MemoryCollection()
    _test_db = SimpleNamespace(cards=cards, private_reference_records=server.MemoryCollection())

    user = server.User(user_id="owner-1", email="owner@example.com", name="Owner")
    character = asyncio.run(server.create_card(server.CardCreate(
        type="character", name="Neris", attributes={"pf_attuali": "18"},
    ), user, db=_test_db))

    first = asyncio.run(server.update_card(character.id, server.CardUpdate(attributes={"pf_attuali": "14"}, version=character.version), user, db=_test_db))
    second = asyncio.run(server.update_card(character.id, server.CardUpdate(attributes={"pf_attuali": "9"}, version=first.version), user, db=_test_db))
    assert first.version == 1
    assert second.version == 2

    undo_second = asyncio.run(server.undo_card_change(character.id, server.CardVersionInput(version=second.version), user, db=_test_db))
    assert undo_second["card"].attributes["pf_attuali"] == "14"
    undo_first = asyncio.run(server.undo_card_change(character.id, server.CardVersionInput(version=undo_second["card"].version), user, db=_test_db))
    assert undo_first["card"].attributes["pf_attuali"] == "18"
    redo_first = asyncio.run(server.redo_card_change(character.id, server.CardVersionInput(version=undo_first["card"].version), user, db=_test_db))
    assert redo_first["card"].attributes["pf_attuali"] == "14"
    redo_second = asyncio.run(server.redo_card_change(character.id, server.CardVersionInput(version=redo_first["card"].version), user, db=_test_db))
    assert redo_second["card"].attributes["pf_attuali"] == "9"

    undo_for_branch = asyncio.run(server.undo_card_change(character.id, server.CardVersionInput(version=redo_second["card"].version), user, db=_test_db))
    asyncio.run(server.update_card(character.id, server.CardUpdate(attributes={"pf_attuali": "7"}, version=undo_for_branch["card"].version), user, db=_test_db))
    try:
        asyncio.run(server.redo_card_change(character.id, server.CardVersionInput(version=undo_for_branch["card"].version + 1), user, db=_test_db))
        assert False, "Expected a new edit to invalidate the redo branch"
    except server.HTTPException as error:
        assert error.status_code == 409


def test_card_update_rejects_a_stale_editor_version_without_changing_history(monkeypatch):
    cards = server.MemoryCollection()
    _test_db = SimpleNamespace(cards=cards, private_reference_records=server.MemoryCollection())

    user = server.User(user_id="owner-1", email="owner@example.com", name="Owner")
    character = asyncio.run(server.create_card(server.CardCreate(
        type="character", name="Neris", attributes={"pf_attuali": "18", "tiri_salvezza": "Forza"},
    ), user, db=_test_db))
    stale_version = character.version
    saved = asyncio.run(server.update_card(
        character.id,
        server.CardUpdate(attributes={"pf_attuali": "14", "tiri_salvezza": "Forza"}, version=stale_version),
        user, db=_test_db))

    try:
        asyncio.run(server.update_card(
            character.id,
            server.CardUpdate(attributes={"pf_attuali": "18", "tiri_salvezza": "Destrezza"}, version=stale_version),
            user, db=_test_db))
        assert False, "Expected the stale save to be rejected"
    except server.HTTPException as error:
        assert error.status_code == 409

    persisted = asyncio.run(server.get_card(character.id, user, db=_test_db))
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
    _test_db = SimpleNamespace(cards=cards, private_reference_records=references)

    user = server.User(user_id="owner-1", email="owner@example.com", name="Owner")

    def assert_conflict(awaitable):
        with pytest.raises(server.HTTPException) as error:
            asyncio.run(awaitable)
        assert error.value.status_code == 409

    manual_card = asyncio.run(server.create_card(server.CardCreate(type="character", name="Manuale"), user, db=_test_db))
    completed = asyncio.run(server.complete_card_from_manuals(
        manual_card.id,
        server.ManualCompletionInput(version=manual_card.version),
        user, db=_test_db))
    assert_conflict(server.complete_card_from_manuals(
        manual_card.id,
        server.ManualCompletionInput(version=manual_card.version),
        user, db=_test_db))
    assert asyncio.run(server.get_card(manual_card.id, user, db=_test_db)).version == completed.version

    reference_card = asyncio.run(server.create_card(server.CardCreate(
        type="character", name="Riferimenti", reference_ids=[reference["id"]],
    ), user, db=_test_db))
    refreshed = asyncio.run(server.refresh_card_reference_updates(
        reference_card.id,
        server.ReferenceUpdateInput(reference_ids=[reference["id"]], version=reference_card.version),
        user, db=_test_db))
    assert_conflict(server.refresh_card_reference_updates(
        reference_card.id,
        server.ReferenceUpdateInput(reference_ids=[reference["id"]], version=reference_card.version),
        user, db=_test_db))
    assert asyncio.run(server.get_card(reference_card.id, user, db=_test_db)).version == refreshed["card"].version

    undo_card = asyncio.run(server.create_card(server.CardCreate(type="character", name="Cronologia"), user, db=_test_db))
    changed = asyncio.run(server.update_card(
        undo_card.id,
        server.CardUpdate(attributes={"pf_attuali": "12"}, version=undo_card.version),
        user, db=_test_db))
    changed_again = asyncio.run(server.update_card(
        undo_card.id,
        server.CardUpdate(attributes={"pf_attuali": "8"}, version=changed.version),
        user, db=_test_db))
    assert_conflict(server.undo_card_change(
        undo_card.id,
        server.CardVersionInput(version=changed.version),
        user, db=_test_db))
    assert asyncio.run(server.get_card(undo_card.id, user, db=_test_db)).version == changed_again.version

    redo_card = asyncio.run(server.create_card(server.CardCreate(type="character", name="Ripristino"), user, db=_test_db))
    changed_for_redo = asyncio.run(server.update_card(
        redo_card.id,
        server.CardUpdate(attributes={"pf_attuali": "12"}, version=redo_card.version),
        user, db=_test_db))
    undone_for_redo = asyncio.run(server.undo_card_change(
        redo_card.id,
        server.CardVersionInput(version=changed_for_redo.version),
        user, db=_test_db))
    refreshed_for_redo = asyncio.run(server.refresh_card_reference_updates(
        redo_card.id,
        server.ReferenceUpdateInput(version=undone_for_redo["card"].version),
        user, db=_test_db))
    assert_conflict(server.redo_card_change(
        redo_card.id,
        server.CardVersionInput(version=undone_for_redo["card"].version),
        user, db=_test_db))
    assert asyncio.run(server.get_card(redo_card.id, user, db=_test_db)).version == refreshed_for_redo["card"].version

    linked_character = asyncio.run(server.create_card(server.CardCreate(
        type="character", name="Carte collegate", reference_ids=[reference["id"]],
    ), user, db=_test_db))
    linked = asyncio.run(server.create_linked_cards(
        linked_character.id,
        server.LinkedCardInput(reference_ids=[reference["id"]], version=linked_character.version),
        user, db=_test_db))
    assert len(linked) == 1
    assert_conflict(server.create_linked_cards(
        linked_character.id,
        server.LinkedCardInput(reference_ids=[reference["id"]], version=linked_character.version),
        user, db=_test_db))
    assert len(cards.rows) == 6

    delete_card = asyncio.run(server.create_card(server.CardCreate(type="character", name="Da eliminare"), user, db=_test_db))
    updated_for_delete = asyncio.run(server.update_card(
        delete_card.id,
        server.CardUpdate(name="Ancora qui", version=delete_card.version),
        user, db=_test_db))
    assert_conflict(server.delete_card(
        delete_card.id,
        server.CardVersionInput(version=delete_card.version),
        user, db=_test_db))
    assert asyncio.run(server.get_card(delete_card.id, user, db=_test_db)).name == "Ancora qui"
    assert asyncio.run(server.delete_card(
        delete_card.id,
        server.CardVersionInput(version=updated_for_delete.version),
        user, db=_test_db)) == {"ok": True}


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
    _test_db = SimpleNamespace(cards=cards, private_reference_records=references)

    user = server.User(user_id="owner-1", email="legacy@example.com", name="Legacy")

    report = asyncio.run(server.card_reference_updates("legacy-character", user, db=_test_db))
    assert report["untracked_count"] == 1
    refreshed = asyncio.run(server.refresh_card_reference_updates(
        "legacy-character",
        server.ReferenceUpdateInput(reference_ids=[record["id"]], version=0),
        user, db=_test_db))
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
    _test_db = SimpleNamespace(cards=cards, private_reference_records=references)

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
    ), user, db=_test_db))

    references.rows[0] = corrected
    report = asyncio.run(server.card_reference_updates(character.id, user, db=_test_db))
    assert report["updated_count"] == 1
    assert "attributi" in report["updates"][0]["changed_fields"]

    refreshed = asyncio.run(server.refresh_card_reference_updates(
        character.id,
        server.ReferenceUpdateInput(reference_ids=[original["id"]], version=character.version),
        user, db=_test_db))
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
    _test_db = SimpleNamespace(cards=cards)


    public_card = asyncio.run(server.public_get_card("public-card", db=_test_db))
    assert public_card["name"] == "Carta pubblica"
    assert "reference_snapshots" not in public_card
    assert "reference_ids" not in public_card
    assert "user_id" not in public_card
    assert "TESTO PRIVATO DEL MANUALE" not in str(public_card)


def test_apply_reference_endpoint_cannot_read_another_users_record(monkeypatch):
    record = make_reference("Tiratore Scelto", user_id="owner-1")
    _test_db = SimpleNamespace(private_reference_records=MemoryReferences([record]))

    other_user = server.User(user_id="owner-2", email="other@example.com", name="Other")

    try:
        asyncio.run(server.apply_private_reference(record["id"], other_user, db=_test_db))
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
    _test_db = SimpleNamespace(cards=cards, private_reference_records=references)

    user = server.User(user_id="owner-1", email="ranger@example.com", name="Ranger")

    with pytest.raises(server.HTTPException, match="da verificare") as create_error:
        asyncio.run(server.create_card(server.CardCreate(
            type="character",
            name="Personaggio",
            reference_ids=[record["id"]],
        ), user, db=_test_db))
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
            user, db=_test_db))
    assert linked_error.value.status_code == 409


def test_generate_content_prefers_matching_private_reference_before_gemini(monkeypatch):
    record = make_reference("Tiratore Scelto")
    _test_db = SimpleNamespace(private_reference_records=MemoryReferences([record]))

    monkeypatch.setattr(lib_mod, "GEMINI_API_KEY", None)
    user = server.User(user_id="owner-1", email="ranger@example.com", name="Ranger", premium_manual=True)

    payload = asyncio.run(server.generate_content(
        server.GenerateContentInput(type="feat", prompt="tirator scelto"),
        user, gemini_key=None, db=_test_db))

    assert payload["source"] == "biblioteca_privata"
    assert payload["name"] == "Tiratore Scelto"


def test_generate_content_labels_manual_content_without_a_trusted_source(monkeypatch):
    record = make_reference(
        "Palla di Fuoco",
        reference_type="spell",
        review_flags=["ocr_da_verificare"],
        review_status="needs_review",
    )
    _test_db = SimpleNamespace(private_reference_records=MemoryReferences([record]))

    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago", premium_manual=True)

    monkeypatch.setattr(lib_mod, "GEMINI_API_KEY", "test-key")
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
        user, gemini_key="test-key", db=_test_db))

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
    _test_db = SimpleNamespace(private_reference_records=MemoryReferences([trusted, unverified]))

    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago")

    sourced = asyncio.run(server.search_private_library(q="Palla di fuoco", types="spell", user=user, db=_test_db))
    unavailable = asyncio.run(server.search_private_library(q="Dardo incantato", types="spell", user=user, db=_test_db))
    diagnostic = asyncio.run(server.search_private_library(
        q="Dardo incantato",
        types="spell",
        include_unverified=True,
        user=user,
        db=_test_db,
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
    monkeypatch.setattr(lib_mod, "available_reference_manuals",
        lambda: {"Manuale-A.pdf": manual_a, "Manuale-B.pdf": manual_b},
    )
    _test_db = SimpleNamespace(private_reference_records=MemoryReferences([
            *verified_records,
            review_in_a,
            review_in_b,
            {**review_in_a, "id": "other-owner-record", "user_id": "owner-2"},
        ]))

    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago")

    result = asyncio.run(server.search_private_library(
        q="",
        types="class",
        review_only=True,
        include_unverified=True,
        source_filename="Manuale-A.pdf",
        user=user,
        db=_test_db,
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
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {"Manuale.pdf": source})
    monkeypatch.setattr(lib_mod, "MANUAL_COVERAGE_CATEGORIES", {"Manuale.pdf": ("class", "subclass", "spell")})

    report = server.manual_coverage_report(records)
    coverage = {item["reference_type"]: item for item in report[0]["categories"]}

    assert coverage["class"] == {"reference_type": "class", "valid": 1, "to_review": 0, "missing": 0, "records_total": 1}
    assert coverage["subclass"] == {"reference_type": "subclass", "valid": 0, "to_review": 1, "missing": 0, "records_total": 1}
    assert coverage["spell"] == {"reference_type": "spell", "valid": 0, "to_review": 0, "missing": 1, "records_total": 0}


def test_coverage_endpoint_includes_translation_pending_in_totals(monkeypatch, tmp_path):
    """GET /library/coverage totals must include translation_pending for rate-limited records."""
    source = tmp_path / "Manuale.pdf"
    source.write_bytes(b"manual")
    records = [
        make_reference(
            "Guerriero",
            reference_type="class",
            source_refs=[{"filename": "Manuale.pdf", "page": 10}],
            review_status="pending",
        ),
        # Rate-limited, not yet verified — must count as translation_pending.
        make_reference(
            "Barbaro",
            reference_type="class",
            source_refs=[{"filename": "Manuale.pdf", "page": 11}],
            translation_status="failed",
            translation_error="provider_rate_limited",
            review_status="pending",
        ),
        # Rate-limited but already verified — must NOT count as translation_pending.
        make_reference(
            "Ladro",
            reference_type="class",
            source_refs=[{"filename": "Manuale.pdf", "page": 12}],
            translation_status="failed",
            translation_error="provider_rate_limited",
            review_status="verified",
        ),
        # Exhausted rate-limit, not verified — must also count.
        make_reference(
            "Mago",
            reference_type="class",
            source_refs=[{"filename": "Manuale.pdf", "page": 13}],
            translation_status="failed",
            translation_error="provider_rate_limited_exhausted",
            review_status="needs_review",
        ),
    ]
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {"Manuale.pdf": source})
    monkeypatch.setattr(lib_mod, "MANUAL_COVERAGE_CATEGORIES", {"Manuale.pdf": ("class",)})
    _test_db = SimpleNamespace(private_reference_records=MemoryReferences(records))


    owner = server.User(user_id="owner-1", email="mago@example.com", name="Mago", premium_manual=True)
    response = asyncio.run(server.private_library_coverage(owner, db=_test_db))

    totals = response["totals"]
    # Barbaro + Mago → 2 unverified rate-limited; Ladro is verified → excluded.
    assert totals["translation_pending"] == 2
    assert "to_review" in totals
    assert "valid" in totals
    assert "missing" in totals


def test_apply_reference_rejects_unverified_records(monkeypatch):
    record = make_reference(
        "Rituale Incerto",
        reference_type="spell",
        review_flags=["traduzione_da_verificare"],
        review_status="needs_review",
    )
    _test_db = SimpleNamespace(private_reference_records=MemoryReferences([record]))

    user = server.User(user_id="owner-1", email="mago@example.com", name="Mago")

    with pytest.raises(server.HTTPException, match="dato certo") as error:
        asyncio.run(server.apply_private_reference(record["id"], user, db=_test_db))

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
    _test_db = SimpleNamespace(
            private_reference_records=collection,
            private_reference_review_history=review_history,
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
        asyncio.run(server.apply_private_reference(record["id"], owner, db=_test_db))

    details = asyncio.run(server.get_private_reference_review(record["id"], owner, db=_test_db))
    assert details["original"]["name"] == "Bárbaro"
    assert details["original"]["full_text"] == "Un guerrero feroz que combate con furia."
    assert details["translation"]["name"] == "Barbaro"
    assert details["translation"]["full_text"] == "Un guerriero feroce che combatte con furia."
    assert details["manual"] == [{"filename": "Manual del Jugador.pdf", "page": 46, "language": "es"}]

    with pytest.raises(server.HTTPException) as other_owner:
        asyncio.run(server.get_private_reference_review(record["id"], other_user, db=_test_db))
    assert other_owner.value.status_code == 404

    rejected = asyncio.run(server.review_private_reference(
        record["id"],
        server.ReferenceReviewInput(
            review_status="needs_review",
            review_notes="Controllare il termine tecnico nella seconda frase.",
        ),
        owner, db=_test_db))
    assert rejected["needs_review"] is True
    assert rejected["review_notes"].startswith("Controllare")
    assert rejected["review_history"][0]["reviewer_id"] == owner.user_id
    assert rejected["review_history"][0]["reviewer_name"] == owner.name
    assert rejected["review_history"][0]["review_status"] == "needs_review"
    assert rejected["review_history"][0]["review_notes"] == "Controllare il termine tecnico nella seconda frase."
    assert rejected["review_history"][0]["reviewed_at"]
    with pytest.raises(server.HTTPException, match="dato certo"):
        asyncio.run(server.apply_private_reference(record["id"], owner, db=_test_db))

    approved = asyncio.run(server.review_private_reference(
        record["id"],
        server.ReferenceReviewInput(
            review_status="verified",
            review_notes="Confrontata con il manuale alla pagina indicata.",
        ),
        owner, db=_test_db))
    assert approved["is_trusted"] is True
    assert approved["review_status"] == "verified"
    assert approved["review_notes"].startswith("Confrontata")
    assert len(approved["review_history"]) == 2
    assert approved["review_history"][0]["review_status"] == "verified"
    assert approved["review_history"][1]["review_status"] == "needs_review"
    assert approved["review_history"][1]["review_notes"].startswith("Controllare")
    assert len(review_history.rows) == 2
    assert asyncio.run(server.apply_private_reference(record["id"], owner, db=_test_db))["name"] == "Barbaro"


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
    _test_db = SimpleNamespace(
            private_reference_records=references,
            private_reference_review_history=review_history,
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
            owner, db=_test_db)

    async def submit_together():
        await asyncio.gather(
            submit("needs_review", "Controllare il nome."),
            submit("verified", "Confrontata riga per riga."),
        )

    asyncio.run(submit_together())

    details = asyncio.run(server.get_private_reference_review(record["id"], owner, db=_test_db))
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
    _test_db = SimpleNamespace(
            private_reference_records=collection,
            private_reference_review_history=review_history,
        )

    owner = server.User(user_id="owner-1", email="mago@example.com", name="Mago", premium_manual=True)

    asyncio.run(server.review_private_reference(
        record["id"],
        server.ReferenceReviewInput(review_status="verified", review_notes=""),
        owner, db=_test_db))

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
    _test_db = SimpleNamespace(
            private_reference_records=collection,
            private_reference_review_history=review_history,
        )

    owner = server.User(user_id="owner-1", email="mago@example.com", name="Mago", premium_manual=True)

    asyncio.run(server.review_private_reference(
        record["id"],
        server.ReferenceReviewInput(review_status="needs_review", review_notes="Da ricontrollare."),
        owner, db=_test_db))

    stored = collection.rows[0]
    assert stored["review_status"] == "needs_review"
    assert stored.get("translation_error") == "provider_rate_limited"


def test_same_source_import_uses_distinct_ids_for_distinct_owners(monkeypatch, tmp_path):
    source = tmp_path / "Manuale.pdf"
    source.write_bytes(b"not-read")
    record = make_reference("Tiratore Scelto")
    collection = MutableMemoryReferences([])
    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {"Manuale.pdf": source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args, **kwargs: SimpleNamespace(records=[record], pages_read=1, pages_needing_ocr=[]),
    )
    body = server.ReferenceImportInput(filenames=["Manuale.pdf"])

    asyncio.run(server.import_private_reference_manuals("owner-1", body, db=_test_db))
    asyncio.run(server.import_private_reference_manuals("owner-2", body, db=_test_db))

    assert len(collection.rows) == 2
    assert collection.rows[0]["id"] != collection.rows[1]["id"]


def test_ocr_import_requires_server_side_confirmation_and_one_manual(monkeypatch, tmp_path):
    first = tmp_path / "Primo.pdf"
    second = tmp_path / "Secondo.pdf"
    first.write_bytes(b"not-read")
    second.write_bytes(b"not-read")
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {"Primo.pdf": first, "Secondo.pdf": second})

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


def test_ocr_import_sends_pages_to_openai_not_gemini(monkeypatch, tmp_path):
    """OCR imports must route pages to OpenAI — the provider named in the consent notice —
    and must never send them to Gemini (generativelanguage.googleapis.com)."""
    import pymupdf as fitz

    # A scan-only PDF: the page has no text layer, so extract_reference_records will
    # invoke the OCR callback for it.
    pdf_path = tmp_path / "Manuale_del_giocatore__1787259882002.pdf"
    doc = fitz.open()
    doc.new_page()  # empty page → forces OCR callback
    doc.save(pdf_path)
    doc.close()

    called_urls: list = []

    class _OpenAIResponse:
        def raise_for_status(self): pass
        def json(self):
            return {
                "choices": [{"message": {"content": "TALENTO DI PROVA\nTesto verificabile della prova."}}]
            }

    def fake_post(url, **kwargs):
        called_urls.append(url)
        return _OpenAIResponse()

    monkeypatch.setattr(server.requests, "post", fake_post)
    monkeypatch.setattr(lib_mod, "OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {pdf_path.name: pdf_path})
    _test_db = SimpleNamespace(private_reference_records=MutableMemoryReferences([]))


    asyncio.run(server.import_private_reference_manuals(
        "owner-ocr",
        server.ReferenceImportInput(
            filenames=[pdf_path.name],
            use_ai_ocr=True,
            start_page=1,
            end_page=1,
            external_processing_confirmed=True,
        ),
        db=_test_db,
    ))

    assert called_urls, "OCR import must invoke an HTTP endpoint"
    for url in called_urls:
        assert "openai.com" in url, (
            f"OCR import must send pages to OpenAI (consented provider), not: {url}"
        )
    assert not any("googleapis.com" in url for url in called_urls), (
        "OCR import must not send pages to Gemini when the user consented to OpenAI"
    )


def test_manual_metadata_uses_the_same_ocr_rule_as_imports():
    assert server.manual_requires_ocr("Manuale_del_giocatore__1787259882002.pdf")
    assert server.manual_requires_ocr("Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf")
    assert server.manual_requires_ocr("724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf")
    assert not server.manual_requires_ocr("Guida_onnicomprensiva_di_Xanathar__1787259928030.pdf")
    assert not server.manual_requires_ocr("731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf")


def test_manual_source_duplicate_detection_compares_required_distinct_assets(monkeypatch, tmp_path):
    monster = tmp_path / "Monster.pdf"
    player = tmp_path / "Player.pdf"
    unrelated = tmp_path / "Unrelated.pdf"
    monster.write_bytes(b"the same supplied manual")
    player.write_bytes(b"the same supplied manual")
    unrelated.write_bytes(b"a different supplied manual")
    manuals = {
        monster.name: monster,
        player.name: player,
        unrelated.name: unrelated,
    }
    monkeypatch.setattr(
        lib_mod,
        "REFERENCE_MANUAL_DISTINCT_CONTENT",
        {monster.name: (player.name,)},
    )

    assert lib_mod.manual_source_duplicate_of(monster.name, manuals) == player.name
    assert lib_mod.manual_source_duplicate_of(unrelated.name, manuals) is None


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

    monkeypatch.setattr(lib_mod, "GEMINI_API_KEY", "test-key")
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

    monkeypatch.setattr(lib_mod, "GEMINI_API_KEY", "gemini-test-key")
    monkeypatch.setattr(lib_mod, "OPENAI_API_KEY", "openai-test-key")
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
    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(records=[record], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch",
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
        db=_test_db,
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
    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(records=[record], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch",
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
        db=_test_db,
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
    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals",
        lambda: {"731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf": source},
    )
    monkeypatch.setattr(lib_mod, "extract_reference_records",
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

    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", translate)
    body = server.ReferenceImportInput(
        filenames=["731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"],
        translation_processing_confirmed=True,
        start_page=5,
        end_page=5,
    )
    first = asyncio.run(server.import_private_reference_manuals("owner-1", body, db=_test_db))
    second = asyncio.run(server.import_private_reference_manuals("owner-1", body, db=_test_db))

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
    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals",
        lambda: {"731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf": source},
    )
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(records=[make_reference("Bárbaro", reference_type="class")], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", lambda batch: ({}, "provider_translation_failed"))

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=["731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=5,
        ),
        db=_test_db,
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

    monkeypatch.setattr(lib_mod, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(lib_mod, "OPENAI_API_KEY", "openai-key")
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

    monkeypatch.setattr(lib_mod, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(lib_mod, "OPENAI_API_KEY", "openai-key")
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

    monkeypatch.setattr(lib_mod, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(lib_mod, "OPENAI_API_KEY", "openai-key")
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
    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(
            records=[make_reference("Bárbaro", reference_type="class")], pages_read=1, pages_needing_ocr=[]
        ),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch",
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
        db=_test_db,
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

    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", lambda batch: next(responses))

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=5,
        ),
        db=_test_db,
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

    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", mock_translate)

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=5,
        ),
        db=_test_db,
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

    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", lambda batch: next(responses))

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            start_page=5,
            end_page=5,
        ),
        db=_test_db,
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

    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron, guerrero], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", mock_translate)

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            translation_batch_size=3,  # keep all 3 records in one batch
            start_page=5,
            end_page=5,
        ),
        db=_test_db,
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

    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron, guerrero], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", mock_translate)

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            translation_batch_size=2,  # batch 1: [Bárbaro, Ladrón], batch 2: [Guerrero]
            start_page=5,
            end_page=5,
        ),
        db=_test_db,
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

    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "extract_reference_records",
        lambda *args: SimpleNamespace(records=[barbaro, ladron], pages_read=1, pages_needing_ocr=[]),
    )
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", mock_translate)

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            translation_processing_confirmed=True,
            translation_batch_size=1,  # force two singleton batches
            start_page=5,
            end_page=5,
        ),
        db=_test_db,
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

    async def fake_retry(user_id, record_id, *, db=None):
        retry_calls.append(record_id)
        # Simulate continued rate-limiting by not changing the record's status.

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(lib_mod, "retry_private_reference_translation", fake_retry)

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

    async def fake_retry(user_id, record_id, *, db=None):
        # Simulate success: clear the rate-limit error from the collection.
        for row in records.rows:
            if row["id"] == record_id:
                row["translation_error"] = ""
                row["translation_status"] = "translated"

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(lib_mod, "retry_private_reference_translation", fake_retry)

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

    async def fake_import(_user_id, body, *, db=None):
        return server.ReferenceImportResult(
            imported=0, updated=0, flagged_for_review=0, skipped=0,
            sources=[{
                "filename": source.name,
                "pages_needing_ocr": [],
                "translation_rate_limited": 1,
            }],
        )

    retry_calls: list[str] = []

    async def fake_retry_rate_limited(user_id, filename, collection, delays=None, job_updater=None, *, db=None):
        retry_calls.append(filename)
        return 0

    _test_db = SimpleNamespace(
        private_manual_import_jobs=jobs,
        private_reference_records=records,
    )

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 1)
    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", fake_import)
    monkeypatch.setattr(preload_mod, "_retry_rate_limited_translations", fake_retry_rate_limited)

    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput(), db=_test_db))
    asyncio.run(server.run_manual_preload_worker("owner-1", db=_test_db))

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

    async def fake_retry(user_id, record_id, *, db=None):
        pass  # Keep record rate-limited to exercise all delay slots.

    async def fake_updater(attempt: int, retry_at: str) -> None:
        # retry_at must be an ISO timestamp and updater must fire BEFORE the sleep.
        updater_calls.append((attempt, retry_at, len(slept)))

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(lib_mod, "retry_private_reference_translation", fake_retry)

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

    async def fake_retry(user_id, record_id, *, db=None):
        retried.append(record_id)
        # All retries keep failing with rate-limit to exercise exhaustion path.

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(lib_mod, "retry_private_reference_translation", fake_retry)

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
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch",
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
    _test_db = SimpleNamespace(private_reference_records=records)


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
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch",
        lambda batch: (translate_calls.append(batch) or ({}, "")),
    )

    async def fake_sleep(_s):
        pass

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    _test_db = SimpleNamespace(private_reference_records=records)


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

    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", translate_and_verify)
    _test_db = SimpleNamespace(private_reference_records=records)


    asyncio.run(server.retry_private_reference_translation("owner-1", "ref-owned-barbaro", db=_test_db))

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

    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", translate)

    result = asyncio.run(server.retry_private_reference_translation("owner-1", source["id"], db=_test_db))

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
            server.retry_private_reference_translation("owner-1", source["id"], db=_test_db)
        )
        assert await asyncio.to_thread(provider_started.wait, 1)
        second = asyncio.create_task(
            server.retry_private_reference_translation("owner-1", source["id"], db=_test_db)
        )
        await asyncio.sleep(0.1)
        assert len(calls) == 1
        allow_provider_result.set()
        return await asyncio.gather(first, second)

    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", translate)

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

    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", translate)

    result = asyncio.run(server.retry_private_reference_translation("owner-1", source["id"], db=_test_db))

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
    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch",
        lambda batch: ({}, "provider_translation_invalid"),
    )

    result = asyncio.run(server.retry_private_reference_translation("owner-1", source["id"], db=_test_db))

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
    _test_db = SimpleNamespace(private_reference_records=collection)

    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", lambda batch: calls.append(batch))

    result = asyncio.run(server.retry_private_reference_translation("owner-1", source["id"], db=_test_db))

    assert result == source
    assert calls == []


def test_retry_translation_endpoint_rejects_non_premium_user_before_provider_call(monkeypatch):
    calls = []

    async def non_premium_user():
        return server.User(user_id="owner-1", email="ranger@example.com", name="Ranger")

    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", lambda batch: calls.append(batch))
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
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})

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


def test_manual_import_progress_exposes_translation_pending_and_failed_counters():
    """records_translation_pending counts rate-limited failures (including exhausted
    retries) not yet verified by a human.  records_translation_failed counts hard
    failures.  Both counters exclude records already manually verified.

    The exhausted state (provider_rate_limited_exhausted) is the terminal value
    written by _retry_rate_limited_translations once a completed job has run
    through all automatic retry slots — it is the primary state the badge must
    detect on completed jobs."""
    records = [
        # exhausted retries after job completion — must count as pending
        make_reference(
            "Barbaro",
            reference_type="class",
            source_language="es",
            source_refs=[{"filename": "Manual.pdf", "page": 1, "language": "es"}],
            translation_status="failed",
            translation_error="provider_rate_limited_exhausted",
            review_status="needs_review",
            review_flags=["traduzione_da_verificare"],
        ),
        # mid-job rate-limited state — also counts as pending
        make_reference(
            "Paladino",
            reference_type="class",
            source_language="es",
            source_refs=[{"filename": "Manual.pdf", "page": 2, "language": "es"}],
            translation_status="failed",
            translation_error="provider_rate_limited",
            review_status="pending",
        ),
        # exhausted but already verified by the user — must NOT count
        make_reference(
            "Guerrero",
            reference_type="class",
            source_language="es",
            source_refs=[{"filename": "Manual.pdf", "page": 3, "language": "es"}],
            translation_status="failed",
            translation_error="provider_rate_limited_exhausted",
            review_status="verified",
        ),
        # hard failure — counts as failed
        make_reference(
            "Druida",
            reference_type="class",
            source_language="es",
            source_refs=[{"filename": "Manual.pdf", "page": 4, "language": "es"}],
            translation_status="failed",
            translation_error="provider_translation_failed",
            review_status="pending",
        ),
        # successfully translated — neither counter
        make_reference(
            "Mago",
            reference_type="class",
            source_language="es",
            source_refs=[{"filename": "Manual.pdf", "page": 5, "language": "es"}],
            translation_status="translated",
            review_status="pending",
        ),
    ]

    progress = server.manual_import_progress("Manual.pdf", records, 10)

    assert progress["records_translation_pending"] == 2, (
        "Both the exhausted-retry and mid-job rate-limited records should be counted; "
        "the verified one must be excluded"
    )
    assert progress["records_translation_failed"] == 1, (
        "Only the unverified hard-failure record should be counted as failed"
    )


def test_spanish_translation_requires_consent_before_provider_call(monkeypatch, tmp_path):
    source = tmp_path / "Manual-del-Jugador.pdf"
    source.write_bytes(b"native-text")
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    calls = []
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "translate_spanish_reference_batch", lambda batch: calls.append(batch))

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
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})

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
    _test_db = SimpleNamespace(private_manual_import_jobs=jobs)

    monkeypatch.setattr(lib_mod, "available_reference_manuals",
        lambda: {
            native.name: native,
            spanish.name: spanish,
            scanned.name: scanned,
        },
    )
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 8)

    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput(), db=_test_db))
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
    _test_db = SimpleNamespace(private_manual_import_jobs=jobs)

    monkeypatch.setattr(lib_mod, "available_reference_manuals",
        lambda: {spanish.name: spanish, other.name: other},
    )
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 1018)

    asyncio.run(server.ensure_manual_preload_jobs(
        "owner-1",
        server.ManualPreloadInput(filename=spanish.name),
        db=_test_db,
    ))

    assert [job["filename"] for job in jobs.rows] == [spanish.name]
    assert jobs.rows[0]["translation_processing_confirmed"] is True


def test_automatic_preload_marks_a_duplicate_manual_source_failed(monkeypatch, tmp_path):
    monster = tmp_path / "Monster.pdf"
    player = tmp_path / "Player.pdf"
    monster.write_bytes(b"same manual bytes")
    player.write_bytes(b"same manual bytes")
    jobs = server.MemoryCollection()
    records = server.MemoryCollection()
    records.rows.extend([
        {
            "id": "invalid-source-record",
            "user_id": "owner-1",
            "source_key": monster.name,
            "source_refs": [{"filename": monster.name, "page": 10}],
            "reference_type": "monster",
            "name": "Mostro errato",
            "normalized_name": "mostro errato",
        },
        {
            "id": "legacy-invalid-source-record",
            "user_id": "owner-1",
            "source_key": "",
            "source_refs": [{"filename": monster.name, "page": 11}],
            "reference_type": "monster",
            "name": "Mostro legacy errato",
            "normalized_name": "mostro legacy errato",
        },
        {
            "id": "valid-source-record",
            "user_id": "owner-1",
            "source_key": player.name,
            "source_refs": [{"filename": player.name, "page": 12}],
            "reference_type": "other",
            "name": "Regola valida",
            "normalized_name": "regola valida",
        },
    ])
    jobs.rows.append({
        "id": "existing-monster-job",
        "user_id": "owner-1",
        "filename": monster.name,
        "source_fingerprint": "old-fingerprint",
        "status": "completed",
        "current_page": 322,
        "records_imported": 3,
        "records_updated": 2,
        "records_flagged": 1,
        "records_skipped": 4,
        "pages_needing_ocr": [8],
    })
    _test_db = SimpleNamespace(
        private_manual_import_jobs=jobs,
        private_reference_records=records,
    )
    manuals = {monster.name: monster, player.name: player}
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: manuals)
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 321)
    monkeypatch.setattr(
        lib_mod,
        "REFERENCE_MANUAL_DISTINCT_CONTENT",
        {monster.name: (player.name,)},
    )

    asyncio.run(server.ensure_manual_preload_jobs(
        "owner-1",
        server.ManualPreloadInput(filename=monster.name),
        db=_test_db,
    ))

    job = jobs.rows[0]
    assert job["status"] == "failed"
    assert job["last_error"] == f"manual_source_duplicate:{player.name}"
    assert job["current_page"] == 1
    assert job["records_imported"] == 0
    assert job["records_updated"] == 0
    assert job["records_flagged"] == 0
    assert job["records_skipped"] == 0
    assert job["pages_needing_ocr"] == []
    remaining = asyncio.run(lib_mod.private_reference_records("owner-1", db=_test_db))
    assert [record["id"] for record in remaining] == ["valid-source-record"]
    assert asyncio.run(lib_mod.find_private_reference(
        "owner-1",
        "Mostro errato",
        db=_test_db,
    )) is None
    coverage = lib_mod.manual_coverage_report(remaining)
    monster_coverage = next(report for report in coverage if report["filename"] == monster.name)
    assert all(category["records_total"] == 0 for category in monster_coverage["categories"])


def test_automatic_preload_processes_all_chunks_without_manual_ranges(monkeypatch, tmp_path):
    source = tmp_path / "Manuale-nativo.pdf"
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    calls = []
    _test_db = SimpleNamespace(private_manual_import_jobs=jobs)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 25)

    async def fake_import(owner_id, body, *, db=None):
        calls.append((owner_id, body.start_page, body.end_page, body.use_ai_ocr, body.auto_accept))
        return server.ReferenceImportResult(
            imported=2,
            updated=1,
            flagged_for_review=1,
            skipped=0,
            sources=[{"filename": source.name, "pages_needing_ocr": []}],
        )

    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", fake_import)
    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput(), db=_test_db))
    asyncio.run(server.run_manual_preload_worker("owner-1", db=_test_db))

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
    _test_db = SimpleNamespace(private_manual_import_jobs=jobs)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 6)

    async def fake_import(_owner_id, body, *, db=None):
        calls.append((body.use_ai_ocr, body.external_processing_confirmed, body.auto_accept))
        return server.ReferenceImportResult(
            imported=1,
            updated=0,
            flagged_for_review=1,
            skipped=0,
            sources=[{"filename": source.name, "pages_needing_ocr": []}],
        )

    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", fake_import)
    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput(), db=_test_db))
    asyncio.run(server.run_manual_preload_worker("owner-1", db=_test_db))

    assert jobs.rows[0]["status"] == "completed"
    assert calls == [(True, True, True)]


def test_spanish_preload_skips_unreadable_cover_pages_and_continues(monkeypatch, tmp_path):
    filename = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    source = tmp_path / filename
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    _test_db = SimpleNamespace(private_manual_import_jobs=jobs)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 2)

    calls = []

    async def fake_import(_user_id, body, *, db=None):
        calls.append(body.use_ai_ocr)
        return server.ReferenceImportResult(
            imported=0, updated=0, flagged_for_review=0, skipped=0,
            sources=[{"filename": filename, "pages_needing_ocr": [1]}],
        )

    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", fake_import)
    asyncio.run(server.ensure_manual_preload_jobs(
        "owner-1",
        server.ManualPreloadInput(filename=filename),
        db=_test_db,
    ))
    asyncio.run(server.run_manual_preload_worker("owner-1", db=_test_db))

    assert jobs.rows[0]["status"] == "completed"
    assert jobs.rows[0]["current_page"] == 3
    assert jobs.rows[0]["pages_needing_ocr"] == [1]
    assert calls == [False]


def test_preload_checkpoint_ignores_a_worker_that_lost_its_lease(monkeypatch, tmp_path):
    source = tmp_path / "Manuale-nativo.pdf"
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    _test_db = SimpleNamespace(private_manual_import_jobs=jobs)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 2)

    async def fake_import(*_args, **_kwargs):
        return server.ReferenceImportResult(
            imported=1, updated=0, flagged_for_review=0, skipped=0,
            sources=[{"filename": source.name, "pages_needing_ocr": []}],
        )

    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", fake_import)
    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput(), db=_test_db))
    claimed = asyncio.run(server.claim_next_manual_preload_job("owner-1", db=_test_db))
    assert claimed and claimed["lease_id"]

    jobs.rows[0]["lease_id"] = "new-owner-lease"
    asyncio.run(server.process_manual_preload_job("owner-1", claimed, db=_test_db))

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
    _test_db = SimpleNamespace(private_manual_import_jobs=jobs)

    started = []
    monkeypatch.setattr(preload_mod, "start_manual_preload_worker", lambda user_id, *, db=None: started.append(user_id))

    asyncio.run(server.resume_manual_preload_workers(db=_test_db))

    assert jobs.rows[0]["status"] == "queued"
    assert jobs.rows[1]["status"] == "processing"
    assert started == ["owner-1"]


def test_startup_requeues_legacy_translation_consent_job_for_processing(monkeypatch, tmp_path):
    source = tmp_path / "Manuale-nativo.pdf"
    source.write_bytes(b"manual")
    jobs = server.MemoryCollection()
    jobs.rows.append({
        "id": "legacy-translation-consent",
        "user_id": "owner-1",
        "filename": source.name,
        "status": "waiting_translation_consent",
        "lease_id": "stale-lease",
        "lease_expires_at": int(time.time()) + 600,
        "last_error": "stale-error",
        "translation_retry_at": "2026-08-24T08:00:00+00:00",
        "translation_retry_attempt": 2,
    })
    _test_db = SimpleNamespace(private_manual_import_jobs=jobs)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 1)
    monkeypatch.setattr(preload_mod, "start_manual_preload_worker", lambda user_id, *, db=None: None)

    async def fake_import(_user_id, body, *, db=None):
        assert body.start_page == 1
        assert body.end_page == 1
        return server.ReferenceImportResult(
            imported=1,
            updated=0,
            flagged_for_review=0,
            skipped=0,
            sources=[{"filename": source.name, "pages_needing_ocr": []}],
        )

    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", fake_import)

    asyncio.run(server.resume_manual_preload_workers(db=_test_db))
    assert jobs.rows[0]["status"] == "queued"
    assert jobs.rows[0]["lease_id"] == ""
    assert jobs.rows[0]["lease_expires_at"] == 0
    assert jobs.rows[0]["last_error"] == ""
    assert jobs.rows[0]["translation_retry_at"] is None
    assert jobs.rows[0]["translation_retry_attempt"] == 0

    asyncio.run(server.run_manual_preload_worker("owner-1", db=_test_db))
    assert jobs.rows[0]["status"] == "completed"


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
    _test_db = SimpleNamespace(private_manual_import_jobs=jobs)

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 1018)
    started = []
    monkeypatch.setattr(preload_mod, "start_manual_preload_worker", lambda user_id, *, db=None: started.append(user_id))

    asyncio.run(server.resume_manual_preload_workers(db=_test_db))

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

    async def fake_import(_user_id, body, *, db=None):
        return server.ReferenceImportResult(
            imported=0, updated=0, flagged_for_review=0, skipped=0,
            sources=[{
                "filename": source.name,
                "pages_needing_ocr": [],
                "translation_rate_limited": 1,
            }],
        )

    updater_snapshots: list[dict] = []

    async def capturing_retry(user_id, filename, collection, delays=None, job_updater=None, *, db=None):
        # Call the updater once as the real function would (attempt 0).
        if job_updater is not None:
            await job_updater(0, "2026-08-23T12:00:30+00:00")
            # Capture the job state immediately after the updater fires.
            if jobs.rows:
                updater_snapshots.append(dict(jobs.rows[0]))
        return 0

    _test_db = SimpleNamespace(
        private_manual_import_jobs=jobs,
        private_reference_records=records,
    )

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 1)
    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", fake_import)
    monkeypatch.setattr(preload_mod, "_retry_rate_limited_translations", capturing_retry)

    asyncio.run(server.ensure_manual_preload_jobs("owner-1", server.ManualPreloadInput(), db=_test_db))
    asyncio.run(server.run_manual_preload_worker("owner-1", db=_test_db))

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

    async def fake_retry(_uid, _rid, *, db=None):
        pass

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(lib_mod, "retry_private_reference_translation", fake_retry)

    # Must not raise even though job_updater is not provided.
    remaining = asyncio.run(
        server._retry_rate_limited_translations(
            "owner-1", "manual.pdf", records, delays=(1,)
        )
    )
    assert remaining == 1  # record still rate-limited → escalated


# ── OCR end-to-end tests ──────────────────────────────────────────────────────


def test_gemini_ocr_returns_transcription_for_valid_response(monkeypatch, tmp_path):
    """gemini_ocr_manual_page must return the OCR text when Gemini responds with a
    well-formed payload, and extract_reference_records must mark those records as
    ocr_da_verificare so they require human verification before use."""
    import pymupdf as fitz
    from reference_library import extract_reference_records

    ocr_text = (
        "TALENTO DELLA PRECISIONE\n"
        "Prerequisito: Destrezza 13. Questo talento migliora la precisione in combattimento"
        " e offre un beneficio verificabile che non viene inventato dal modello.\n"
    )
    valid_payload = {
        "candidates": [{"content": {"parts": [{"text": ocr_text}]}}]
    }

    monkeypatch.setattr(server.requests, "post", lambda *a, **k: _OcrResponse(payload=valid_payload))
    monkeypatch.setattr(lib_mod, "GEMINI_API_KEY", "test-key")

    returned = server.gemini_ocr_manual_page(_OcrPage(), 5)

    assert returned == ocr_text.strip()
    assert "TALENTO DELLA PRECISIONE" in returned

    # Records produced from OCR text must carry the unverified flag.
    pdf_path = tmp_path / "scan.pdf"
    doc = fitz.open()
    doc.new_page()   # empty page → forces OCR callback
    doc.save(pdf_path)
    doc.close()

    report = extract_reference_records(pdf_path, ocr_page=lambda _page, _num: ocr_text)

    assert report.pages_read == 1
    assert report.pages_needing_ocr == []
    assert len(report.records) == 1
    assert report.records[0]["reference_type"] == "feat"
    assert "ocr_da_verificare" in report.records[0]["review_flags"]
    assert not reference_is_trusted(report.records[0])



def test_extract_reference_records_handles_ocr_only_manual_with_mixed_pages(tmp_path):
    """A manual where some pages are readable, one succeeds via OCR, and one fails OCR
    must report pages_read, pages_needing_ocr, and OCR-flagged records correctly."""
    import pymupdf as fitz
    from reference_library import extract_reference_records

    pdf_path = tmp_path / "dm-guide-scan.pdf"
    doc = fitz.open()

    # Page 1: readable text layer
    p1 = doc.new_page()
    p1.insert_text(
        (72, 72),
        "MOSTRO ESEMPLARE\n"
        "Il dungeon master usa questi mostri come sfida per i giocatori nella campagna.\n"
        "Il testo contiene abbastanza dettagli verificabili da produrre un record valido.\n",
    )
    # Page 2: empty (OCR will succeed)
    doc.new_page()
    # Page 3: empty (OCR will fail)
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    def ocr_callback(page, page_number):
        if page_number == 2:
            return (
                "TRAPPOLA NASCOSTA\n"
                "Prerequisito: Destrezza 13. La trappola si attiva solo al tocco e offre"
                " un effetto verificabile che il DM può usare in scena.\n"
            )
        return ""   # page 3 fails OCR

    report = extract_reference_records(pdf_path, ocr_page=ocr_callback)

    assert report.pages_read == 2             # page 1 (native) + page 2 (OCR)
    assert report.pages_needing_ocr == [3]    # page 3 failed OCR

    names = [r["name"] for r in report.records]
    assert any("Trappola" in n for n in names), "OCR-sourced record from page 2 must be extracted"

    ocr_records = [r for r in report.records if "ocr_da_verificare" in r["review_flags"]]
    assert len(ocr_records) >= 1, "Records extracted via OCR must carry ocr_da_verificare"

    native_records = [r for r in report.records if "ocr_da_verificare" not in r["review_flags"]]
    assert len(native_records) >= 1, "Records from the native text layer must NOT carry ocr_da_verificare"


def test_preload_worker_marks_job_failed_after_max_ocr_attempts(monkeypatch, tmp_path):
    """process_manual_preload_job must set status=failed and last_error=ocr_pages_unavailable
    when an OCR-only manual exhausts all permitted retry attempts."""
    source = tmp_path / "dm-guide-scan.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF")
    filename = source.name
    lease_id = "lease-retry-exhausted"

    jobs = server.MemoryCollection()
    jobs.rows.append({
        "id": "job-ocr-max-1",
        "user_id": "owner-1",
        "filename": filename,
        "status": "processing",
        "source_fingerprint": "fp-dm",
        "current_page": 1,
        "page_count": 3,
        "attempt_count": server.MANUAL_PRELOAD_MAX_ATTEMPTS - 1,  # one more failure → failed
        "last_error": "ocr_pages_unavailable",
        "pages_needing_ocr": [1],
        "records_imported": 0,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "lease_id": lease_id,
        "lease_expires_at": int(time.time()) + 300,
        "translation_processing_confirmed": True,
        "external_processing_confirmed": True,
        "updated_at": "2026-08-01T00:00:00+00:00",
    })

    async def fake_import(_user_id, body, *, db=None):
        # The OCR page still fails — simulates a page that cannot be transcribed.
        return server.ReferenceImportResult(
            imported=0, updated=0, flagged_for_review=0, skipped=0,
            sources=[{"filename": filename, "pages_needing_ocr": [1], "translation_rate_limited": 0}],
        )

    _test_db = SimpleNamespace(
        private_manual_import_jobs=jobs,
        private_reference_records=server.MemoryCollection(),
    )

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 3)
    monkeypatch.setattr(lib_mod, "manual_requires_ocr", lambda _fn: True)
    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", fake_import)

    asyncio.run(server.process_manual_preload_job("owner-1", dict(jobs.rows[0]), db=_test_db))

    final_job = jobs.rows[0]
    assert final_job["status"] == "failed", (
        "Job must be failed after exhausting MANUAL_PRELOAD_MAX_ATTEMPTS OCR retries"
    )
    assert final_job["last_error"] == "ocr_pages_unavailable"
    assert 1 in final_job["pages_needing_ocr"]


def test_preload_worker_accumulates_pages_needing_ocr_across_chunks(monkeypatch, tmp_path):
    """pages_needing_ocr must accumulate correctly: pages from previous chunks that lie
    outside the current batch are preserved, and newly unreadable pages are added."""
    source = tmp_path / "dm-guide-scan.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF")
    filename = source.name
    lease_id = "lease-accumulate"

    jobs = server.MemoryCollection()
    jobs.rows.append({
        "id": "job-ocr-accum-1",
        "user_id": "owner-1",
        "filename": filename,
        "status": "processing",
        "source_fingerprint": "fp-dm2",
        "current_page": 13,            # starting a new batch at page 13
        "page_count": 30,
        "attempt_count": 0,
        "last_error": "",
        "pages_needing_ocr": [1, 2],   # leftovers from earlier batches
        "records_imported": 5,
        "records_updated": 0,
        "records_flagged": 0,
        "records_skipped": 0,
        "lease_id": lease_id,
        "lease_expires_at": int(time.time()) + 300,
        "translation_processing_confirmed": True,
        "external_processing_confirmed": True,
        "updated_at": "2026-08-01T00:00:00+00:00",
    })

    async def fake_import(_user_id, body, *, db=None):
        # Page 13 (inside the current batch) also fails OCR.
        return server.ReferenceImportResult(
            imported=3, updated=0, flagged_for_review=0, skipped=0,
            sources=[{"filename": filename, "pages_needing_ocr": [13], "translation_rate_limited": 0}],
        )

    _test_db = SimpleNamespace(
        private_manual_import_jobs=jobs,
        private_reference_records=server.MemoryCollection(),
    )

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "manual_page_count", lambda _path: 30)
    monkeypatch.setattr(lib_mod, "manual_requires_ocr", lambda _fn: True)
    monkeypatch.setattr(lib_mod, "import_private_reference_manuals", fake_import)

    asyncio.run(server.process_manual_preload_job("owner-1", dict(jobs.rows[0]), db=_test_db))

    final_job = jobs.rows[0]
    # Pages 1 and 2 are outside the current batch (13–24) → preserved.
    # Page 13 newly failed within the batch → added.
    assert sorted(final_job["pages_needing_ocr"]) == [1, 2, 13], (
        "pages_needing_ocr must merge prior unresolved pages with newly failed ones"
    )
    assert final_job["records_imported"] == 8   # 5 previous + 3 new


# ---------------------------------------------------------------------------
# OCR guard tests – HTTP-layer enforcement before any page reaches Gemini
# ---------------------------------------------------------------------------

def _make_gemini_must_not_be_called():
    """Return a requests.post replacement that raises if Gemini is invoked."""
    def _forbidden(*args, **kwargs):
        raise AssertionError(
            "requests.post must not be called: a guard should have rejected the request "
            "before any page image was sent to Gemini."
        )
    return _forbidden


def test_http_ocr_import_requires_consent_even_with_active_preload_worker(
    monkeypatch, tmp_path
):
    """An active preload worker must not grant consent to a user-facing import."""
    from core.db import get_db

    source = tmp_path / "Manuale-Scansionato.pdf"
    source.write_bytes(b"scan")
    filename = source.name
    test_db = SimpleNamespace(
        private_manual_import_jobs=server.MemoryCollection(),
        private_reference_records=server.MemoryCollection(),
    )
    requests_post = Mock(name="requests_post")

    async def premium_user():
        return server.User(
            user_id="owner-1",
            email="mago@example.com",
            name="Mago",
            premium_manual=True,
        )

    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(server.requests, "post", requests_post)
    server.app.dependency_overrides[server.get_current_user] = premium_user
    server.app.dependency_overrides[get_db] = lambda: test_db
    preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS.add("owner-1")
    try:
        with TestClient(server.app) as client:
            response = client.post(
                "/api/library/import",
                json={
                    "filenames": [filename],
                    "start_page": 1,
                    "end_page": 5,
                    "use_ai_ocr": True,
                },
            )
    finally:
        server.app.dependency_overrides.pop(server.get_current_user, None)
        server.app.dependency_overrides.pop(get_db, None)
        preload_mod.MANUAL_PRELOAD_ACTIVE_WORKERS.discard("owner-1")

    assert response.status_code == 400
    assert "esplicitamente" in response.json()["detail"]
    requests_post.assert_not_called()


def test_ocr_import_blocks_missing_consent_before_any_page_reaches_gemini(
    monkeypatch, tmp_path
):
    """use_ai_ocr=True without external_processing_confirmed must raise HTTP 400
    before any call to requests.post (i.e. before any page is sent to Gemini)."""
    source = tmp_path / "Manuale-Scansionato.pdf"
    source.write_bytes(b"scan")
    filename = source.name
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(server.requests, "post", _make_gemini_must_not_be_called())

    try:
        asyncio.run(server.import_private_reference_manuals(
            "owner-1",
            server.ReferenceImportInput(
                filenames=[filename],
                use_ai_ocr=True,
                external_processing_confirmed=False,
                start_page=1,
                end_page=5,
            ),
        ))
        assert False, "Expected HTTP 400 when external_processing_confirmed is missing"
    except server.HTTPException as error:
        assert error.status_code == 400
        assert "Gemini" in error.detail or "esplicitamente" in error.detail or "pagine selezionate" in error.detail


def test_ocr_import_blocks_spanish_manual_before_any_page_reaches_gemini(
    monkeypatch, tmp_path
):
    """use_ai_ocr=True on a Spanish (native-text) manual must raise HTTP 400 and
    must not dispatch any page to Gemini, even when all consent flags are set."""
    source = tmp_path / "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
    source.write_bytes(b"native-text")
    filename = source.name
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(server.requests, "post", _make_gemini_must_not_be_called())

    try:
        asyncio.run(server.import_private_reference_manuals(
            "owner-1",
            server.ReferenceImportInput(
                filenames=[filename],
                use_ai_ocr=True,
                external_processing_confirmed=True,
                translation_processing_confirmed=True,
                start_page=5,
                end_page=10,
            ),
        ))
        assert False, "Expected HTTP 400 for OCR on a native-text Spanish manual"
    except server.HTTPException as error:
        assert error.status_code == 400
        assert "testo nativo" in error.detail


def test_ocr_import_blocks_oversized_range_before_any_page_reaches_gemini(
    monkeypatch, tmp_path
):
    """use_ai_ocr=True with more than 12 pages (or no end_page) must raise HTTP 400
    before dispatching any page to Gemini."""
    source = tmp_path / "Manuale-Scansionato.pdf"
    source.write_bytes(b"scan")
    filename = source.name
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(server.requests, "post", _make_gemini_must_not_be_called())

    # No end_page at all
    try:
        asyncio.run(server.import_private_reference_manuals(
            "owner-1",
            server.ReferenceImportInput(
                filenames=[filename],
                use_ai_ocr=True,
                external_processing_confirmed=True,
                start_page=1,
                end_page=None,
            ),
        ))
        assert False, "Expected HTTP 400 when end_page is absent for OCR import"
    except server.HTTPException as error:
        assert error.status_code == 400
        assert "12" in error.detail or "intervallo" in error.detail

    # end_page set but range exceeds 12 pages
    try:
        asyncio.run(server.import_private_reference_manuals(
            "owner-1",
            server.ReferenceImportInput(
                filenames=[filename],
                use_ai_ocr=True,
                external_processing_confirmed=True,
                start_page=1,
                end_page=14,
            ),
        ))
        assert False, "Expected HTTP 400 when OCR range exceeds 12 pages"
    except server.HTTPException as error:
        assert error.status_code == 400
        assert "12" in error.detail


def test_ocr_import_blocks_multiple_manuals_before_any_page_reaches_gemini(
    monkeypatch, tmp_path
):
    """use_ai_ocr=True with more than one manual filename must raise HTTP 400
    before any page is sent to Gemini."""
    source_a = tmp_path / "Manuale-A.pdf"
    source_b = tmp_path / "Manuale-B.pdf"
    source_a.write_bytes(b"scan-a")
    source_b.write_bytes(b"scan-b")
    monkeypatch.setattr(lib_mod, "available_reference_manuals",
        lambda: {source_a.name: source_a, source_b.name: source_b},
    )
    monkeypatch.setattr(server.requests, "post", _make_gemini_must_not_be_called())

    try:
        asyncio.run(server.import_private_reference_manuals(
            "owner-1",
            server.ReferenceImportInput(
                filenames=[source_a.name, source_b.name],
                use_ai_ocr=True,
                external_processing_confirmed=True,
                start_page=1,
                end_page=5,
            ),
        ))
        assert False, "Expected HTTP 400 when OCR is requested for multiple manuals"
    except server.HTTPException as error:
        assert error.status_code == 400
        assert "solo manuale" in error.detail or "un solo" in error.detail


def test_valid_ocr_import_sends_each_selected_page_once_and_persists_review_flags(
    monkeypatch, tmp_path
):
    """A confirmed OCR import must process only the requested pages once each.

    OCR-derived records are persisted, but every one remains blocked behind the
    human-review flag until someone verifies the transcription.
    """
    import pymupdf as fitz

    source = tmp_path / "Manuale-Scansionato.pdf"
    document = fitz.open()
    for _ in range(4):
        document.new_page()
    document.save(source)
    document.close()

    filename = source.name
    records_from_pages = ("TALENTO OCR DUE", "TALENTO OCR TRE")
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        title = records_from_pages[len(calls) - 1]
        return _OcrResponse(
            payload={
                "choices": [{
                    "message": {
                        "content": (
                            f"{title}\n"
                            "Prerequisito: Destrezza 13. Questo talento migliora la "
                            "precisione in combattimento e offre un beneficio "
                            "verificabile descritto nella pagina del manuale."
                        )
                    }
                }]
            }
        )

    collection = server.MemoryCollection()
    test_db = SimpleNamespace(private_reference_records=collection)
    monkeypatch.setattr(lib_mod, "available_reference_manuals", lambda: {filename: source})
    monkeypatch.setattr(lib_mod, "manual_requires_ocr", lambda _filename: True)
    monkeypatch.setattr(lib_mod, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(server.requests, "post", fake_post)

    result = asyncio.run(server.import_private_reference_manuals(
        "owner-1",
        server.ReferenceImportInput(
            filenames=[filename],
            start_page=2,
            end_page=3,
            use_ai_ocr=True,
            external_processing_confirmed=True,
        ),
        db=test_db,
    ))

    assert len(calls) == 2
    assert all(url == "https://api.openai.com/v1/chat/completions" for url, _ in calls)
    assert result.imported == 2
    assert result.flagged_for_review == 2
    assert len(collection.rows) == 2
    assert {
        normalize_reference_name(record["name"]) for record in collection.rows
    } == {
        normalize_reference_name(title) for title in records_from_pages
    }
    assert {record["source_refs"][0]["page"] for record in collection.rows} == {2, 3}
    assert all("ocr_da_verificare" in record["review_flags"] for record in collection.rows)
    assert not [
        record for record in collection.rows
        if "ocr_da_verificare" not in record["review_flags"]
    ]
