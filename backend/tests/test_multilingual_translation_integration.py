import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.db import MemoryCollection
from schemas.library import ReferenceImportInput
from services import library


def _record(record_id="source-rule"):
    return {
        "id": record_id,
        "reference_type": "other",
        "name": "Original Rule",
        "normalized_name": "original rule",
        "description": "Original source description.",
        "full_text": "Original complete source rules text with 1d6 damage.",
        "attributes": {"damage": "1d6"},
        "tags": [],
        "source_refs": [{"filename": "source.pdf", "page": 1}],
        "review_flags": [],
        "parent_class": "",
        "parent_subclass": "",
        "level": "",
    }


def _prepare(monkeypatch, tmp_path, language):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"unused")
    collection = MemoryCollection()
    db = SimpleNamespace(private_reference_records=collection)
    monkeypatch.setattr(library, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(library, "manual_source_duplicate_of", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(library, "manual_forces_ocr", lambda _filename: False)
    monkeypatch.setattr(library, "manual_source_language", lambda _filename: language)
    monkeypatch.setattr(library, "manual_source_metadata", lambda _filename: {
        "title": "Source Manual",
        "language": language,
        "native_text": True,
    })
    monkeypatch.setattr(library, "extract_reference_records", lambda *_args, **_kwargs: SimpleNamespace(
        records=[_record()], pages_read=1, pages_needing_ocr=[]
    ))
    return source, collection, db


@pytest.mark.parametrize("language", ["en", "ru"])
def test_import_translates_supported_non_italian_manuals_and_preserves_source(monkeypatch, tmp_path, language):
    source, collection, db = _prepare(monkeypatch, tmp_path, language)
    calls = []

    def fake_translate(records, source_language):
        calls.append(source_language)
        return {
            records[0]["id"]: {
                "name": "Regola Tradotta",
                "description": "Descrizione tradotta.",
                "full_text": "Testo tradotto completo con 1d6 danni.",
                "attributes": {"damage": "1d6"},
            }
        }, ""

    monkeypatch.setattr(library, "translate_reference_batch", fake_translate)

    result = asyncio.run(library.import_private_reference_manuals(
        "owner",
        ReferenceImportInput(
            filenames=[source.name], start_page=1, end_page=1,
            translation_processing_confirmed=True, auto_accept=True,
        ),
        db=db,
    ))

    assert calls == [language]
    assert result.imported == 1
    stored = collection.rows[0]
    assert stored["name"] == "Regola Tradotta"
    assert stored["source_name"] == "Original Rule"
    assert stored["source_full_text"].startswith("Original complete")
    assert stored["translation_status"] == "translated"
    assert "traduzione_da_verificare" not in stored.get("review_flags", [])
    assert stored["review_status"] == "needs_review"
    assert stored["ai_review_status"] == "pending"


@pytest.mark.parametrize("language", ["en", "ru", "es"])
def test_import_requires_translation_processing_confirmation_for_supported_languages(monkeypatch, tmp_path, language):
    source, _collection, db = _prepare(monkeypatch, tmp_path, language)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(library.import_private_reference_manuals(
            "owner",
            ReferenceImportInput(filenames=[source.name], start_page=1, end_page=1),
            db=db,
        ))
    assert exc.value.status_code == 400
    assert "traduzione" in exc.value.detail.casefold()


def test_italian_import_never_calls_translation_provider(monkeypatch, tmp_path):
    source, collection, db = _prepare(monkeypatch, tmp_path, "it")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Italian source must not be translated")

    monkeypatch.setattr(library, "translate_reference_batch", fail_if_called)
    result = asyncio.run(library.import_private_reference_manuals(
        "owner",
        ReferenceImportInput(filenames=[source.name], start_page=1, end_page=1, auto_accept=True),
        db=db,
    ))

    assert result.imported == 1
    stored = collection.rows[0]
    assert stored["translation_status"] == "not_required"
    assert stored["source_name"] == "Original Rule"


def test_translation_progress_counts_english_and_russian_pending_records():
    records = [
        {
            "source_refs": [{"filename": "book.pdf", "page": 1}],
            "source_language": "en",
            "translation_status": "failed",
            "translation_error": "provider_rate_limited",
            "review_status": "needs_review",
            "review_flags": [],
        },
        {
            "source_refs": [{"filename": "book.pdf", "page": 2}],
            "source_language": "ru",
            "translation_status": "translated",
            "review_status": "needs_review",
            "review_flags": [],
        },
    ]

    progress = library.manual_import_progress("book.pdf", records, 2)
    assert progress["translation_total"] == 2
    assert progress["records_translated"] == 1
    assert progress["records_translation_pending"] == 1
