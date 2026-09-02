from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "backend/services/library.py"
TEST = ROOT / "backend/tests/test_multilingual_translation_integration.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_pos = text.find(start)
    if start_pos < 0:
        raise SystemExit(f"{label}: start marker not found")
    end_pos = text.find(end, start_pos)
    if end_pos < 0:
        raise SystemExit(f"{label}: end marker not found")
    return text[:start_pos] + replacement + text[end_pos:]


text = LIB.read_text()

# Import only the generic provider-independent language policy. Existing import
# state/flag semantics remain unchanged so rate-limit retries keep working.
text = replace_once(
    text,
    "from schemas.library import ReferenceImportInput, ReferenceImportResult\n\nlogger = logging.getLogger(\"tomeforge\")\n",
    "from schemas.library import ReferenceImportInput, ReferenceImportResult\n"
    "from services.reference_translation import (\n"
    "    build_translation_prompt,\n"
    "    normalize_language,\n"
    "    translation_required,\n"
    "    validate_translation_payload,\n"
    ")\n\n"
    "logger = logging.getLogger(\"tomeforge\")\n",
    "translation imports",
)

new_translation_functions = '''def translate_reference_batch(
    records: list[dict],
    source_language: str,
) -> tuple[dict[str, dict], str]:
    """Translate a small structured EN/ES/RU batch without sending PDF pages."""
    if not records:
        return {}, ""
    source_language = normalize_language(source_language)
    try:
        prompt = build_translation_prompt(records, source_language)
    except ValueError as exc:
        return {}, str(exc)
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TEXT_MODEL}:generateContent",
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                    "maxOutputTokens": 8192,
                },
            },
            timeout=(15, 120),
        )
        response.raise_for_status()
        decoded = _json_from_model_text(_gemini_text_from_response(response.json()))
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as exc:
        primary_rate_limited = _is_provider_rate_limited(exc)
        logger.warning(
            "Traduzione Gemini %s->it non disponibile per un gruppo di %s record: %s; provo OpenAI autorizzato",
            source_language,
            len(records),
            exc,
        )
        try:
            decoded = _openai_translation_response(prompt)
        except (requests.RequestException, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as fallback_exc:
            logger.warning(
                "Traduzione OpenAI %s->it non disponibile per un gruppo di %s record: %s",
                source_language,
                len(records),
                fallback_exc,
            )
            if primary_rate_limited or _is_provider_rate_limited(fallback_exc):
                return {}, "provider_rate_limited"
            return {}, "provider_translation_failed"

    return validate_translation_payload(decoded, records)


def translate_spanish_reference_batch(records: list[dict]) -> tuple[dict[str, dict], str]:
    """Backward-compatible Spanish translation entry point."""
    return translate_reference_batch(records, "es")


def _translate_reference_batch_for_language(
    records: list[dict], source_language: str
) -> tuple[dict[str, dict], str]:
    """Keep Spanish monkeypatch compatibility while supporting EN/RU."""
    source_language = normalize_language(source_language)
    if source_language == "es":
        return translate_spanish_reference_batch(records)
    return translate_reference_batch(records, source_language)


'''
text = replace_between(
    text,
    "def translate_spanish_reference_batch(records: list[dict])",
    "async def private_reference_records",
    new_translation_functions,
    "translation provider function",
)

new_translation_validation = '''    translatable_manuals = [
        filename for filename in requested
        if translation_required(manual_source_language(filename))
    ]
    if translatable_manuals and not body.translation_processing_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Conferma esplicitamente l'invio del testo estratto al provider AI per la traduzione italiana",
        )
    if translatable_manuals:
        if body.end_page is None:
            raise HTTPException(
                status_code=400,
                detail="Per tradurre un manuale non italiano seleziona un intervallo di massimo 12 pagine",
            )
        if body.end_page - body.start_page + 1 > 12:
            raise HTTPException(
                status_code=400,
                detail="La traduzione dei manuali non italiani è limitata a 12 pagine per importazione",
            )
'''
text = replace_between(
    text,
    "    spanish_manuals = [",
    "    if body.use_ai_ocr:",
    new_translation_validation,
    "translation validation",
)

text = replace_once(
    text,
    '        if record["source_language"] != "es":\n',
    '        if not translation_required(record["source_language"]):\n',
    "translation queue language gate",
)

new_batch_builder = '''    translation_batches: list[tuple[str, list[dict]]] = []
    queues_by_language: dict[str, list[dict]] = {}
    for record in translation_queue:
        queues_by_language.setdefault(normalize_language(record["source_language"]), []).append(record)
    for source_language, language_queue in queues_by_language.items():
        current_batch: list[dict] = []
        current_size = 0
        for record in language_queue:
            record_size = len(record["source_name"]) + len(record["source_description"]) + len(record["source_full_text"])
            if current_batch and (
                len(current_batch) >= body.translation_batch_size
                or current_size + record_size > 12000
            ):
                translation_batches.append((source_language, current_batch))
                current_batch = []
                current_size = 0
            current_batch.append(record)
            current_size += record_size
        if current_batch:
            translation_batches.append((source_language, current_batch))

    provider_exhausted = False
'''
text = replace_between(
    text,
    "    translation_batches: list[list[dict]] = []",
    "    provider_exhausted = False\n",
    new_batch_builder,
    "translation batch builder",
)

text = replace_once(
    text,
    "    for batch in translation_batches:\n",
    "    for source_language, batch in translation_batches:\n",
    "translation batch loop",
)
text = replace_once(
    text,
    "            translated, error = await asyncio.to_thread(translate_spanish_reference_batch, batch)\n",
    "            translated, error = await asyncio.to_thread(\n"
    "                _translate_reference_batch_for_language, batch, source_language\n"
    "            )\n",
    "translation provider batch call",
)
text = replace_once(
    text,
    "                        translate_spanish_reference_batch, [record]\n",
    "                        _translate_reference_batch_for_language, [record], source_language\n",
    "translation provider individual call",
)

old_original = '''    original = {
        "name": record.get("source_name") or (record.get("name") if source_language != "es" else ""),
        "description": record.get("source_description") or (
            record.get("description") if source_language != "es" else ""
        ),
        "full_text": record.get("source_full_text") or (
            record.get("full_text") if source_language != "es" else ""
        ),
        "attributes": copy.deepcopy(
            record.get("source_attributes")
            or (record.get("attributes") if source_language != "es" else {})
            or {}
        ),
    }
'''
new_original = '''    source_is_translated = translation_required(source_language)
    original = {
        "name": record.get("source_name") or (record.get("name") if not source_is_translated else ""),
        "description": record.get("source_description") or (
            record.get("description") if not source_is_translated else ""
        ),
        "full_text": record.get("source_full_text") or (
            record.get("full_text") if not source_is_translated else ""
        ),
        "attributes": copy.deepcopy(
            record.get("source_attributes")
            or (record.get("attributes") if not source_is_translated else {})
            or {}
        ),
    }
'''
text = replace_once(text, old_original, new_original, "review original fallback")

text = replace_once(
    text,
    '        record.get("source_language") == "es"\n        and record.get("translation_status", "not_required") not in {"translated", "failed", TRANSLATION_PROCESSING_STATUS}\n',
    '        translation_required(record.get("source_language"))\n        and record.get("translation_status", "not_required") not in {"translated", "failed", TRANSLATION_PROCESSING_STATUS}\n',
    "translation progress language gate",
)

text = replace_once(
    text,
    '    """Retry one failed Spanish translation without re-reading the manual."""\n',
    '    """Retry one failed EN/ES/RU translation without re-reading the manual."""\n',
    "retry docstring",
)
text = replace_once(
    text,
    '    if record.get("source_language") != "es":\n        raise HTTPException(status_code=400, detail="Questo record non richiede una traduzione dallo spagnolo")\n',
    '    source_language = normalize_language(record.get("source_language"))\n'
    '    if not translation_required(source_language):\n'
    '        raise HTTPException(status_code=400, detail="Questo record non richiede una traduzione italiana")\n',
    "retry language gate",
)
text = replace_once(
    text,
    "        translated, error = await asyncio.to_thread(translate_spanish_reference_batch, [source_record])\n",
    "        translated, error = await asyncio.to_thread(\n"
    "            _translate_reference_batch_for_language, [source_record], source_language\n"
    "        )\n",
    "retry provider call",
)

LIB.write_text(text)

TEST.write_text(r'''import asyncio
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
''')

print("MULTILINGUAL_TRANSLATION_INTEGRATION_PATCH_OK")
