import asyncio
import base64
import copy
import json
import logging
import re
import time
import uuid
from functools import partial
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional

import requests
from fastapi import HTTPException
from reference_sources import (
    source_default_language,
    source_is_rule_source,
    source_metadata_for_page,
    source_requires_vision,
)
from reference_library import (
    CARD_TYPE_BY_REFERENCE_TYPE,
    REFERENCE_TYPES,
    clean_text,
    compact_text,
    extract_reference_records,
    merge_reference_records,
    normalize_reference_name,
    reference_content_fingerprint,
    reference_effective_level,
    reference_effective_type,
    reference_is_trusted,
    reference_review_reason,
    reference_review_state,
    search_reference_records,
)

from core.config import (
    GEMINI_API_KEY,
    GEMINI_TEXT_MODEL,
    MANUAL_COVERAGE_CATEGORIES,
    OPENAI_API_KEY,
    OPENAI_OCR_MODEL,
    OPENAI_TEXT_MODEL,
    REFERENCE_MANUAL_FILENAMES,
    REFERENCE_MANUAL_DISTINCT_CONTENT,
    REFERENCE_MANUAL_METADATA,
    REFERENCE_MANUAL_PARSER_REVISIONS,
    OCR_ONLY_REFERENCE_MANUAL_FILENAMES,
    OCR_REQUIRED_REFERENCE_PREFIXES,
    SPELL_PDF_DIRECTORY,
    TRANSLATION_PROCESSING_STATUS,
    TRANSLATION_LEASE_SECONDS,
    TRANSLATION_POLL_INTERVAL_SECONDS,
    TRANSLATION_WAIT_SECONDS,
    utc_now,
)
from core.db import db as _singleton_db
from schemas.library import ReferenceImportInput, ReferenceImportResult

logger = logging.getLogger("tomeforge")


def is_rule_manual_filename(filename: str) -> bool:
    """Accept safe new PDFs while honoring explicit registry exclusions."""
    lowered = filename.casefold()

    # Character sheets/templates are documents, never rule manuals.
    if (
        lowered.startswith("scheda_personaggio")
        or lowered.startswith("scheda personaggio")
    ):
        return False

    # Known sources obey the explicit source registry. This preserves
    # exclusions for duplicates, obsolete sources and non-rule documents.
    registered = source_metadata_for_page(filename)
    if registered:
        return source_is_rule_source(filename)

    # An unregistered PDF remains discoverable as a candidate source.
    # Its metadata/authority must still be established before canonical use.
    return True


def _registry_available_reference_manuals() -> dict[str, Path]:
    """Discover supplied PDFs from the fixed local assets directory."""
    known = [
        filename for filename in REFERENCE_MANUAL_FILENAMES
        if (SPELL_PDF_DIRECTORY / filename).is_file() and is_rule_manual_filename(filename)
    ]
    known_set = set(known)
    additional = sorted(
        path.name for path in SPELL_PDF_DIRECTORY.glob("*.pdf")
        if path.is_file() and path.name not in known_set and is_rule_manual_filename(path.name)
    )
    return {filename: SPELL_PDF_DIRECTORY / filename for filename in [*known, *additional]}



def available_reference_manuals() -> dict[str, Path]:
    """Registry sources plus safe discovery of additional supplied PDFs."""
    manuals = (
        dict(_registry_available_reference_manuals())
        if REFERENCE_MANUAL_FILENAMES
        else {}
    )

    for source_path in sorted(SPELL_PDF_DIRECTORY.glob("*.pdf")):
        if (
            source_path.is_file()
            and is_rule_manual_filename(source_path.name)
        ):
            manuals.setdefault(source_path.name, source_path)

    return manuals


def _registry_manual_requires_ocr(filename: str) -> bool:
    registered = source_metadata_for_page(filename)
    if registered:
        return source_requires_vision(filename)
    return (
        filename in OCR_ONLY_REFERENCE_MANUAL_FILENAMES
        or filename.startswith(OCR_REQUIRED_REFERENCE_PREFIXES)
    )



def manual_requires_ocr(filename: str) -> bool:
    registered = source_metadata_for_page(filename)
    legacy_requires_ocr = (
        filename in OCR_ONLY_REFERENCE_MANUAL_FILENAMES
        or filename.startswith(OCR_REQUIRED_REFERENCE_PREFIXES)
    )

    return (
        legacy_requires_ocr
        or _registry_manual_requires_ocr(filename)
        or registered.get("text_mode") == "mixed"
    )


def manual_forces_ocr(filename: str) -> bool:
    """Whether every page must use OCR rather than its native text layer."""
    metadata = source_metadata_for_page(filename)
    return bool(metadata and metadata.get("text_mode") == "vision_required") or (
        not metadata and (
            filename in OCR_ONLY_REFERENCE_MANUAL_FILENAMES
            or filename.startswith(OCR_REQUIRED_REFERENCE_PREFIXES)
        )
    )


def manual_source_metadata(filename: str) -> dict:
    registered = source_metadata_for_page(filename)
    if registered:
        return {
            "title": registered["title"],
            "language": registered["language"],
            "native_text": registered.get("text_mode") in {"text", "mixed"},
            "logical_source_id": registered["logical_source_id"],
            "ruleset": registered["ruleset"],
            "authority_class": registered["authority_class"],
            "source_role": registered["source_role"],
            "source_status": registered["source_status"],
            "page_start": registered["page_start"],
            "page_end": registered["page_end"],
            "text_mode": registered["text_mode"],
        }
    return {
        "title": Path(filename).stem.replace("_", " "),
        "language": "it",
        "native_text": not manual_requires_ocr(filename),
        **REFERENCE_MANUAL_METADATA.get(filename, {}),
    }


def manual_source_language(filename: str) -> str:
    return source_default_language(filename) if source_metadata_for_page(filename) else manual_source_metadata(filename)["language"]


def manual_source_fingerprint(path: Path) -> str:
    stat = path.stat()
    value = f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}"
    parser_revision = REFERENCE_MANUAL_PARSER_REVISIONS.get(path.name)
    if parser_revision:
        value = f"{value}:parser:{parser_revision}"
    return sha256(value.encode("utf-8")).hexdigest()


def manual_source_duplicate_of(
    filename: str,
    manuals: Optional[dict[str, Path]] = None,
) -> Optional[str]:
    """Return the conflicting manual filename when two required-distinct PDFs match.

    Compare the actual bytes only after the cheap size check. This keeps normal
    preload setup fast while ensuring a copied asset cannot be indexed under a
    different manual's name.
    """
    required_distinct_from = REFERENCE_MANUAL_DISTINCT_CONTENT.get(filename, ())
    if not required_distinct_from:
        return None
    available = manuals if manuals is not None else available_reference_manuals()
    path = available.get(filename)
    if path is None:
        return None
    try:
        own_size = path.stat().st_size
    except OSError:
        return None
    for other_filename in required_distinct_from:
        other_path = available.get(other_filename)
        if other_path is None:
            continue
        try:
            if own_size != other_path.stat().st_size:
                continue
            if sha256(path.read_bytes()).digest() == sha256(other_path.read_bytes()).digest():
                return other_filename
        except OSError:
            continue
    return None


def manual_page_count(path: Path) -> Optional[int]:
    try:
        import pymupdf as fitz
        document = fitz.open(path)
        page_count = len(document)
        document.close()
        return page_count
    except Exception:
        return None


def gemini_ocr_manual_page(page: Any, page_number: int, source_language: str = "") -> str:
    """Transcribe a private scanned page using Gemini Vision without persisting the image."""
    if not GEMINI_API_KEY:
        logger.warning("OCR Gemini non configurato: GEMINI_API_KEY mancante")
        return ""
    import pymupdf as fitz
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.45, 1.45), alpha=False)
    image_b64 = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
    language_hint = f" La lingua dichiarata della fonte è {source_language}." if source_language else ""
    prompt = (
        "Trascrivi fedelmente la pagina nella sua lingua originale; non tradurre."
        f"{language_hint} Mantieni titoli, paragrafi e tabelle leggibili. Non riassumere, "
        "non inventare testo e non aggiungere commenti: restituisci solo la trascrizione."
    )
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TEXT_MODEL}:generateContent",
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0, "maxOutputTokens": 4096},
            },
            timeout=(15, 180),
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        logger.warning("OCR Gemini non disponibile per pagina %s (HTTP %s)", page_number, status_code or "errore")
        return ""
    except requests.RequestException as exc:
        logger.warning("OCR Gemini non raggiungibile per pagina %s: %s", page_number, exc)
        return ""
    try:
        return _gemini_text_from_response(response.json())
    except (ValueError, TypeError, IndexError, AttributeError) as exc:
        logger.warning("OCR Gemini ha restituito una risposta non leggibile per pagina %s: %s", page_number, exc)
    return ""


def openai_ocr_manual_page(page: Any, page_number: int, source_language: str = "") -> str:
    """Transcribe a private scanned page using OpenAI Vision without persisting the image."""
    if not OPENAI_API_KEY:
        logger.warning("OCR OpenAI non configurato: OPENAI_API_KEY mancante")
        return ""
    import pymupdf as fitz
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.45, 1.45), alpha=False)
    image_b64 = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
    language_hint = f" La lingua dichiarata della fonte è {source_language}." if source_language else ""
    prompt = (
        "Trascrivi fedelmente la pagina nella sua lingua originale; non tradurre."
        f"{language_hint} Mantieni titoli, paragrafi e tabelle leggibili. Non riassumere, "
        "non inventare testo e non aggiungere commenti: restituisci solo la trascrizione."
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_OCR_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "high",
                            }},
                        ],
                    }
                ],
                "temperature": 0,
                "max_tokens": 4096,
            },
            timeout=(15, 180),
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        logger.warning("OCR OpenAI non disponibile per pagina %s (HTTP %s)", page_number, status_code or "errore")
        return ""
    except requests.RequestException as exc:
        logger.warning("OCR OpenAI non raggiungibile per pagina %s: %s", page_number, exc)
        return ""
    try:
        payload = response.json()
        transcription = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if transcription:
            letters = sum(c.isalpha() for c in transcription)
            printable = sum(c.isprintable() for c in transcription)
            logger.info(
                "OCR OpenAI pagina %s: len=%d alpha=%.0f%% printable=%.0f%%",
                page_number,
                len(transcription),
                100 * letters / max(len(transcription), 1),
                100 * printable / max(len(transcription), 1),
            )
            return transcription
        logger.warning("OCR OpenAI senza testo per pagina %s", page_number)
    except (ValueError, TypeError, IndexError, AttributeError) as exc:
        logger.warning("OCR OpenAI ha restituito una risposta non leggibile per pagina %s: %s", page_number, exc)
    return ""


def _gemini_text_from_response(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("risposta JSON non oggetto")
    candidates = payload.get("candidates")
    candidate = candidates[0] if isinstance(candidates, list) and candidates else {}
    if not isinstance(candidate, dict):
        raise ValueError("candidato non valido")
    content = candidate.get("content")
    parts = content.get("parts") if isinstance(content, dict) else []
    if not isinstance(parts, list):
        raise ValueError("parti non valide")
    text = "\n".join(
        part.get("text", "") for part in parts if isinstance(part, dict) and part.get("text")
    ).strip()
    if not text:
        raise ValueError("risposta senza testo")
    return text


def _openai_text_from_response(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("risposta OpenAI non oggetto")
    choices = payload.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else {}
    message = choice.get("message") if isinstance(choice, dict) else {}
    content = message.get("content") if isinstance(message, dict) else ""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("risposta OpenAI senza testo")
    return content.strip()


def _json_from_model_text(text: str) -> object:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _openai_translation_response(prompt: str) -> object:
    if not OPENAI_API_KEY:
        raise RuntimeError("fallback OpenAI non configurato")
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_TEXT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Restituisci esclusivamente il JSON richiesto. "
                        "Non aggiungere testo introduttivo o markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 8192,
        },
        timeout=(15, 120),
    )
    response.raise_for_status()
    return _json_from_model_text(_openai_text_from_response(response.json()))


def _is_provider_rate_limited(exc: Exception) -> bool:
    return (
        isinstance(exc, requests.HTTPError)
        and getattr(getattr(exc, "response", None), "status_code", None) == 429
    )


def translate_spanish_reference_batch(records: list[dict]) -> tuple[dict[str, dict], str]:
    """Translate a small structured Spanish batch without sending PDF pages."""
    if not records:
        return {}, ""
    source_records = [
        {
            "id": record["id"],
            "name": record["source_name"],
            "description": record["source_description"],
            "full_text": record["source_full_text"],
            "attributes": record.get("source_attributes", {}),
        }
        for record in records
    ]
    prompt = (
        "Traduci dallo spagnolo all'italiano questi record strutturati di un manuale "
        "di gioco. Traduci soltanto nome, descrizione e valori di attributes; non "
        "aggiungere regole, non riassumere, non omettere dettagli, non alterare ID, "
        "dadi, numeri, prezzi o nomi delle chiavi. full_text deve contenere la "
        "traduzione completa del testo sorgente, senza abbreviazioni. Restituisci esclusivamente JSON "
        "valido nel formato {\"records\":[{\"id\":\"...\",\"name\":\"...\","
        "\"description\":\"...\",\"full_text\":\"...\",\"attributes\":{...}}]}. Ogni ID ricevuto deve "
        "comparire esattamente una volta.\n\n"
        + json.dumps(source_records, ensure_ascii=False, separators=(",", ":"))
    )
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
            "Traduzione Gemini non disponibile per un gruppo di %s record: %s; provo OpenAI autorizzato",
            len(records), exc,
        )
        try:
            decoded = _openai_translation_response(prompt)
        except (requests.RequestException, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as fallback_exc:
            logger.warning(
                "Traduzione OpenAI non disponibile per un gruppo di %s record: %s",
                len(records), fallback_exc,
            )
            if primary_rate_limited or _is_provider_rate_limited(fallback_exc):
                return {}, "provider_rate_limited"
            return {}, "provider_translation_failed"

    translated_rows = decoded.get("records") if isinstance(decoded, dict) else None
    if not isinstance(translated_rows, list):
        return {}, "provider_translation_invalid"
    expected_ids = {record["id"] for record in records}
    translated: dict[str, dict] = {}
    for item in translated_rows:
        if not isinstance(item, dict) or item.get("id") not in expected_ids:
            continue
        name = clean_text(str(item.get("name") or ""))
        description = clean_text(str(item.get("description") or ""))
        full_text = clean_text(str(item.get("full_text") or ""))
        attributes = item.get("attributes")
        if name and description and full_text and isinstance(attributes, dict):
            translated[item["id"]] = {
                "name": name,
                "description": compact_text(description),
                "full_text": full_text,
                "attributes": attributes,
            }
    if set(translated) != expected_ids:
        return {}, "provider_translation_incomplete"
    return translated, ""


async def private_reference_records(user_id: str, *, db=None) -> list[dict]:
    """Load a user's non-spell manual facts only; the source PDFs stay local."""
    _db = db if db is not None else _singleton_db
    collection = getattr(_db, "private_reference_records", None)
    if collection is None:
        return []
    try:
        return await collection.find({"user_id": user_id}).to_list(8000)
    except Exception as exc:
        if "private_reference_records" in str(exc):
            logger.warning("Private reference catalogue schema is not available yet")
            return []
        raise


async def discard_private_manual_source_records(
    user_id: str,
    source_filename: str,
    *,
    db=None,
) -> int:
    """Remove owner records tied to a source that has been proven invalid.

    `source_key` is the canonical source identifier. Checking `source_refs` as
    well safely cleans records created before that column was backfilled, so an
    invalid source cannot remain searchable or inflate manual coverage.
    """
    _db = db if db is not None else _singleton_db
    collection = getattr(_db, "private_reference_records", None)
    if collection is None:
        return 0
    records = await private_reference_records(user_id, db=_db)
    invalid_ids = [
        record.get("id")
        for record in records
        if (
            record.get("source_key") == source_filename
            or any(
                ref.get("filename") == source_filename
                for ref in record.get("source_refs") or []
                if isinstance(ref, dict)
            )
        )
        and record.get("id")
    ]
    deleted = 0
    for reference_id in invalid_ids:
        result = await collection.delete_one({"id": reference_id, "user_id": user_id})
        deleted += int(getattr(result, "deleted_count", 0))
    return deleted


async def private_manual_import_jobs(user_id: str, *, db=None) -> list[dict]:
    """Load only owner-scoped preload metadata, never manual source material."""
    _db = db if db is not None else _singleton_db
    collection = getattr(_db, "private_manual_import_jobs", None)
    if collection is None:
        return []
    try:
        return await collection.find({"user_id": user_id}).to_list(200)
    except Exception as exc:
        if "private_manual_import_jobs" in str(exc):
            logger.warning("Automatic manual preload schema is not available yet")
            return []
        raise


async def find_private_reference(user_id: str, query: str, card_type: Optional[str] = None, *, db=None) -> Optional[dict]:
    records = await private_reference_records(user_id, db=db)
    matches = search_reference_records(records, query, limit=20)
    if card_type:
        matches = [
            record
            for record in matches
            if CARD_TYPE_BY_REFERENCE_TYPE.get(
                reference_effective_type(record)
            ) == card_type
        ]
    return next((record for record in matches if reference_is_trusted(record)), None)


async def import_private_reference_manuals(user_id: str, body: ReferenceImportInput, *, db=None) -> ReferenceImportResult:
    """Import source records locally, translating Spanish facts in small batches."""
    _db = db if db is not None else _singleton_db
    manuals = available_reference_manuals()
    requested = body.filenames or list(manuals)
    unknown = sorted(set(requested) - set(manuals))
    if unknown:
        raise HTTPException(status_code=400, detail="Uno o più manuali richiesti non sono disponibili localmente")
    duplicate_sources = {
        filename: duplicate_of
        for filename in requested
        if (duplicate_of := manual_source_duplicate_of(filename, manuals))
    }
    if duplicate_sources:
        duplicate_filename, original_filename = next(iter(duplicate_sources.items()))
        raise HTTPException(
            status_code=409,
            detail=(
                f"Il file di {manual_source_metadata(duplicate_filename)['title']} è identico a "
                f"{manual_source_metadata(original_filename)['title']}; sostituisci il PDF con la fonte corretta "
                "prima di importarlo."
            ),
        )
    if body.end_page and body.end_page < body.start_page:
        raise HTTPException(status_code=400, detail="L'intervallo di pagine non è valido")
    spanish_manuals = [
        filename for filename in requested
        if manual_source_language(filename) == "es"
    ]
    if spanish_manuals and not body.translation_processing_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Conferma esplicitamente l'invio del testo estratto a Gemini per la traduzione italiana",
        )
    if spanish_manuals:
        if body.end_page is None:
            raise HTTPException(
                status_code=400,
                detail="Per tradurre il manuale spagnolo seleziona un intervallo di massimo 12 pagine",
            )
        if body.end_page - body.start_page + 1 > 12:
            raise HTTPException(
                status_code=400,
                detail="La traduzione del manuale spagnolo è limitata a 12 pagine per importazione",
            )
    if body.use_ai_ocr:
        spanish_native_manuals = [
            filename for filename in requested
            if manual_source_language(filename) == "es"
        ]
        if spanish_native_manuals:
            raise HTTPException(
                status_code=400,
                detail="Questo manuale ha testo nativo: l'OCR non è consentito e non verranno inviate pagine a OpenAI",
            )
        if not body.external_processing_confirmed:
            raise HTTPException(
                status_code=400,
                detail="Conferma esplicitamente l'invio delle sole pagine selezionate a OpenAI per l'OCR",
            )
        if len(requested) != 1:
            raise HTTPException(status_code=400, detail="L'OCR può elaborare un solo manuale per volta")
        if body.end_page is None:
            raise HTTPException(
                status_code=400,
                detail="Per l'OCR seleziona un piccolo intervallo di pagine (massimo 12) così l'importazione resta verificabile",
            )
        if body.end_page - body.start_page + 1 > 12:
            raise HTTPException(status_code=400, detail="L'OCR OpenAI è limitato a 12 pagine per importazione")

    all_records: list[dict] = []
    source_reports: list[dict] = []
    for filename in requested:
        source_metadata = manual_source_metadata(filename)
        ocr_callback = (
            partial(openai_ocr_manual_page, source_language=source_metadata["language"])
            if body.use_ai_ocr else None
        )
        report = await asyncio.to_thread(
            extract_reference_records,
            manuals[filename],
            ocr_callback,
            body.start_page,
            body.end_page,
            manual_forces_ocr(filename),
            source_metadata["language"],
        )
        for record in report.records:
            source_name = record["name"]
            source_description = record["description"]
            source_full_text = record["full_text"]
            source_normalized_name = record["normalized_name"]
            source_checksum = sha256(
                f"{source_name}\n{source_full_text}".encode("utf-8")
            ).hexdigest()
            all_records.append({
                **record,
                "source_key": filename,
                "source_language": source_metadata["language"],
                "source_normalized_name": source_normalized_name,
                "source_name": source_name,
                "source_description": source_description,
                "source_full_text": source_full_text,
                "source_attributes": dict(record.get("attributes") or {}),
                "source_text_checksum": source_checksum,
            })
        source_reports.append({
            "filename": filename,
            "title": source_metadata["title"],
            "source_language": source_metadata["language"],
            "native_text": source_metadata["native_text"],
            "pages_read": report.pages_read,
            "pages_needing_ocr": report.pages_needing_ocr,
            "records_detected": len(report.records),
            "translated": 0,
            "translation_failed": 0,
            "translation_rate_limited": 0,
            "translation_reused": 0,
        })

    all_records = merge_reference_records(all_records)
    collection = getattr(_db, "private_reference_records", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Biblioteca privata non disponibile: applica prima la migrazione SQL")

    existing_records = await private_reference_records(user_id, db=_db)
    existing_by_source = {
        (
            record.get("reference_type"),
            record.get("source_key"),
            record.get("source_normalized_name") or record.get("normalized_name"),
        ): record
        for record in existing_records
    }
    existing_by_source_name = {
        (
            record.get("source_key"),
            record.get("source_normalized_name") or record.get("normalized_name"),
        ): record
        for record in existing_records
        if record.get("source_key") and (
            record.get("source_normalized_name") or record.get("normalized_name")
        )
    }
    existing_by_storage_key = {
        (
            record.get("reference_type"),
            record.get("source_key"),
            record.get("normalized_name") or normalize_reference_name(record.get("name", "")),
        ): record
        for record in existing_records
        if record.get("reference_type") and record.get("source_key")
    }
    def existing_for_import(record: dict) -> Optional[dict]:
        source_match = existing_by_source.get((
            record["reference_type"],
            record["source_key"],
            record["source_normalized_name"],
        ))
        if source_match:
            return source_match
        source_name_match = existing_by_source_name.get((
            record["source_key"],
            record["source_normalized_name"],
        ))
        if source_name_match:
            return source_name_match
        stored_name_match = existing_by_storage_key.get((
            record["reference_type"],
            record["source_key"],
            record["normalized_name"],
        ))
        if stored_name_match:
            return stored_name_match
        return None

    localized_records: list[dict] = []
    translation_queue: list[dict] = []
    report_by_filename = {report["filename"]: report for report in source_reports}
    for record in merge_reference_records(all_records):
        existing = existing_for_import(record)
        if record["source_language"] != "es":
            localized_records.append({
                **record,
                "translation_status": "not_required",
                "translation_error": "",
            })
            continue
        if (
            existing
            and existing.get("translation_status") == "translated"
            and existing.get("source_text_checksum") == record["source_text_checksum"]
        ):
            localized_records.append({
                **record,
                "name": existing["name"],
                "normalized_name": existing["normalized_name"],
                "description": existing["description"],
                "full_text": existing["full_text"],
                "attributes": dict(existing.get("attributes") or {}),
                "translation_status": "translated",
                "translation_error": "",
            })
            report_by_filename[record["source_key"]]["translation_reused"] += 1
            continue
        translation_queue.append(record)

    translation_batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_size = 0
    for record in translation_queue:
        record_size = len(record["source_name"]) + len(record["source_description"]) + len(record["source_full_text"])
        if current_batch and (
            len(current_batch) >= body.translation_batch_size
            or current_size + record_size > 12000
        ):
            translation_batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(record)
        current_size += record_size
    if current_batch:
        translation_batches.append(current_batch)

    provider_exhausted = False

    for batch in translation_batches:
        individual_errors: dict[str, str] = {}

        if provider_exhausted:
            translated: dict = {}
            error = "provider_rate_limited"
            for record in batch:
                individual_errors[record["id"]] = "provider_rate_limited"
        else:
            translated, error = await asyncio.to_thread(translate_spanish_reference_batch, batch)

            if error == "provider_rate_limited" and len(batch) > 1:
                provider_still_limited = False
                for record in batch:
                    if provider_still_limited:
                        individual_errors[record["id"]] = "provider_rate_limited"
                        continue
                    ind_translated, ind_error = await asyncio.to_thread(
                        translate_spanish_reference_batch, [record]
                    )
                    if ind_translated.get(record["id"]):
                        translated[record["id"]] = ind_translated[record["id"]]
                    elif ind_error == "provider_rate_limited":
                        individual_errors[record["id"]] = "provider_rate_limited"
                        provider_still_limited = True
                    else:
                        individual_errors[record["id"]] = ind_error or "provider_rate_limited"

                if provider_still_limited:
                    provider_exhausted = True
            elif error == "provider_rate_limited":
                provider_exhausted = True

        for record in batch:
            translated_record = translated.get(record["id"])
            report = report_by_filename[record["source_key"]]
            record_error = individual_errors.get(record["id"], error)
            if translated_record:
                name = translated_record["name"]
                description = translated_record["description"]
                localized_records.append({
                    **record,
                    "name": name,
                    "normalized_name": normalize_reference_name(name),
                    "description": description,
                    "full_text": translated_record["full_text"],
                    "attributes": translated_record["attributes"],
                    "translation_status": "translated",
                    "translation_error": "",
                })
                report["translated"] += 1
            elif record_error == "provider_rate_limited":
                localized_records.append({
                    **record,
                    "translation_status": "failed",
                    "translation_error": "provider_rate_limited",
                })
                report["translation_rate_limited"] += 1
            else:
                localized_records.append({
                    **record,
                    "review_flags": sorted(set(record.get("review_flags") or []) | {"traduzione_da_verificare"}),
                    "translation_status": "failed",
                    "translation_error": record_error or "provider_translation_failed",
                })
                report["translation_failed"] += 1

    imported = updated = flagged = skipped = 0
    for record in localized_records:
        if not record.get("name") or not record.get("full_text"):
            skipped += 1
            continue
        existing = existing_for_import(record)
        owned_record_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{user_id}:{record['id']}").hex
        payload = {
            **record,
            "id": f"ref_{owned_record_id}",
            "user_id": user_id,
            "review_status": (
                "verified" if body.auto_accept and reference_review_state(record) == "valid"
                else "needs_review" if reference_review_state(record) == "review" else "pending"
            ),
            "review_notes": "",
            "canonical_id": None,
            "ai_review_status": "pending",
            "ai_confidence": 0,
            "ai_review_model": "",
            "ai_reviewed_at": None,
            "ai_review_notes": "",
            "ai_review_corrections": {},
            "updated_at": utc_now(),
        }

        def _merge_into_existing(base: dict, incoming: dict, rec: dict) -> None:
            incoming["id"] = base["id"]
            incoming["source_refs"] = list(base.get("source_refs") or [])
            incoming["source_refs"].extend(
                ref for ref in rec.get("source_refs", [])
                if ref not in incoming["source_refs"]
            )
            incoming["source_key"] = base.get("source_key") or incoming["source_key"]
            incoming["source_normalized_name"] = (
                base.get("source_normalized_name") or incoming["source_normalized_name"]
            )
            unchanged_source = base.get("source_text_checksum") == rec.get("source_text_checksum")
            source_changed_after_review = (
                not unchanged_source
                and (
                    base.get("review_status") == "verified"
                    or bool(base.get("review_corrections"))
                )
            )
            pending_changed_source = (
                unchanged_source
                and (base.get("review_corrections") or {}).get("_source_changed") is True
            )
            # Preserve explicit owner corrections when the same source is
            # re-imported by the automatic queue. The raw source snapshot
            # remains untouched so the reviewer can still compare both.
            if unchanged_source and base.get("review_corrections") and not pending_changed_source:
                corrections = base["review_corrections"]
                for field_name in ("name", "description", "full_text", "attributes"):
                    if field_name in corrections:
                        incoming[field_name] = copy.deepcopy(corrections[field_name])
                if corrections.get("name"):
                    incoming["normalized_name"] = normalize_reference_name(corrections["name"])
                incoming["review_corrections"] = copy.deepcopy(corrections)
            elif source_changed_after_review:
                # A changed source invalidates every prior human correction.
                # The sentinel survives automatic reimports until a reviewer
                # explicitly verifies the new extraction.
                incoming["review_corrections"] = {"_source_changed": True}
                incoming["review_status"] = "needs_review"
                incoming["review_notes"] = ""
                incoming["canonical_id"] = None
                incoming["ai_review_status"] = "pending"
                incoming["ai_confidence"] = 0
                incoming["ai_review_model"] = ""
                incoming["ai_reviewed_at"] = None
                incoming["ai_review_notes"] = ""
                incoming["ai_review_corrections"] = {}
            elif pending_changed_source:
                incoming["review_corrections"] = {"_source_changed": True}
                incoming["review_status"] = "needs_review"
                incoming["review_notes"] = base.get("review_notes", "")
            if unchanged_source and rec.get("translation_status") != "failed" and not body.auto_accept:
                incoming["review_status"] = base.get("review_status", incoming["review_status"])
                incoming["review_notes"] = base.get("review_notes", "")
                if base.get("review_status") == "verified":
                    # Preserve human corrections while the immutable imported
                    # source checksum is unchanged. A genuinely changed source
                    # still replaces these fields and re-enters review.
                    for field_name in (
                        "name",
                        "normalized_name",
                        "description",
                        "full_text",
                        "attributes",
                    ):
                        incoming[field_name] = copy.deepcopy(base.get(field_name))
                for field_name in (
                    "canonical_id", "ai_review_status", "ai_confidence",
                    "ai_review_model", "ai_reviewed_at", "ai_review_notes",
                    "ai_review_corrections",
                ):
                    incoming[field_name] = copy.deepcopy(base.get(field_name))

        def _refresh_lookup_caches(stored: dict, merged: dict) -> None:
            combined = {**stored, **merged}
            existing_by_storage_key[(
                merged["reference_type"],
                merged.get("source_key", ""),
                merged["normalized_name"],
            )] = combined
            existing_by_source[(
                merged["reference_type"],
                merged.get("source_key", ""),
                merged.get("source_normalized_name") or merged["normalized_name"],
            )] = combined
            existing_by_source_name[(
                merged.get("source_key", ""),
                merged.get("source_normalized_name") or merged["normalized_name"],
            )] = combined

        if existing:
            _merge_into_existing(existing, payload, record)
            try:
                await collection.update_one({"id": existing["id"], "user_id": user_id}, {"$set": payload})
                _refresh_lookup_caches(existing, payload)
                updated += 1
            except Exception as upd_exc:
                if "23505" not in str(upd_exc) and "duplicate key" not in str(upd_exc).lower():
                    raise
                target_rows = (
                    collection.client
                    .table("private_reference_records")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("reference_type", payload["reference_type"])
                    .eq("normalized_name", payload["normalized_name"])
                    .eq("source_key", payload.get("source_key", ""))
                    .limit(1)
                    .execute()
                )
                if target_rows.data:
                    target = target_rows.data[0]
                    merged_refs = list(target.get("source_refs") or [])
                    for ref in (existing.get("source_refs") or []) + (record.get("source_refs") or []):
                        if ref not in merged_refs:
                            merged_refs.append(ref)
                    await collection.update_one(
                        {"id": target["id"], "user_id": user_id},
                        {"$set": {"source_refs": merged_refs, "updated_at": utc_now()}},
                    )
                    if existing["id"] != target["id"]:
                        await collection.delete_one({"id": existing["id"], "user_id": user_id})
                    _refresh_lookup_caches(target, {**target, "source_refs": merged_refs})
                    updated += 1
                else:
                    skipped += 1
        else:
            payload["imported_at"] = utc_now()
            try:
                await collection.insert_one(payload)
                _refresh_lookup_caches({}, payload)
                imported += 1
            except Exception as insert_exc:
                if "23505" not in str(insert_exc) and "duplicate key" not in str(insert_exc).lower():
                    raise
                dup: Optional[dict] = None
                # Search by PK without filtering on user_id: the constraint
                # violation tells us the ID exists; we need to find it even if
                # a previous import saved it under a mismatched user_id.
                pk_rows = (
                    collection.client
                    .table("private_reference_records")
                    .select("*")
                    .eq("id", payload["id"])
                    .limit(1)
                    .execute()
                )
                if pk_rows.data:
                    existing_row = pk_rows.data[0]
                    # Accept only if the conflicting record belongs to this user;
                    # a cross-user ID collision means we cannot safely overwrite it.
                    if existing_row.get("user_id") == user_id:
                        dup = existing_row
                    else:
                        skipped += 1
                        continue
                if dup is None:
                    name_rows = (
                        collection.client
                        .table("private_reference_records")
                        .select("*")
                        .eq("user_id", user_id)
                        .eq("reference_type", payload["reference_type"])
                        .eq("normalized_name", payload["normalized_name"])
                        .eq("source_key", payload.get("source_key", ""))
                        .limit(1)
                        .execute()
                    )
                    if name_rows.data:
                        dup = name_rows.data[0]
                if dup is None:
                    # Cannot locate the conflicting row — skip this record so the
                    # rest of the import batch continues instead of aborting.
                    skipped += 1
                    continue
                _merge_into_existing(dup, payload, record)
                try:
                    await collection.update_one(
                        {"id": dup["id"], "user_id": user_id}, {"$set": payload}
                    )
                    _refresh_lookup_caches(dup, payload)
                    updated += 1
                except Exception as upd2_exc:
                    if "23505" not in str(upd2_exc) and "duplicate key" not in str(upd2_exc).lower():
                        raise
                    target2_rows = (
                        collection.client
                        .table("private_reference_records")
                        .select("*")
                        .eq("user_id", user_id)
                        .eq("reference_type", payload["reference_type"])
                        .eq("normalized_name", payload["normalized_name"])
                        .eq("source_key", payload.get("source_key", ""))
                        .limit(1)
                        .execute()
                    )
                    if target2_rows.data:
                        t2 = target2_rows.data[0]
                        merged_refs = list(t2.get("source_refs") or [])
                        for ref in (dup.get("source_refs") or []) + (record.get("source_refs") or []):
                            if ref not in merged_refs:
                                merged_refs.append(ref)
                        await collection.update_one(
                            {"id": t2["id"], "user_id": user_id},
                            {"$set": {"source_refs": merged_refs, "updated_at": utc_now()}},
                        )
                        if dup["id"] != t2["id"]:
                            await collection.delete_one({"id": dup["id"], "user_id": user_id})
                        _refresh_lookup_caches(t2, {**t2, "source_refs": merged_refs})
                        updated += 1
                    else:
                        skipped += 1
        flagged += reference_review_state(payload) == "review"
    return ReferenceImportResult(
        imported=imported,
        updated=updated,
        flagged_for_review=flagged,
        skipped=skipped,
        sources=source_reports,
    )


def reference_summary(record: dict) -> dict:
    review_state = reference_review_state(record)
    attributes = record.get("attributes") or {}
    effective_type = reference_effective_type(record)
    effective_level = reference_effective_level(record)
    return {
        "id": record["id"],
        "name": record["name"],
        "reference_type": effective_type,
        "source_reference_type": record.get("reference_type", "other"),
        "attributes": attributes,
        "parent_class": record.get("parent_class") or attributes.get("parent_class", ""),
        "parent_subclass": record.get("parent_subclass") or attributes.get("parent_subclass", ""),
        "level": effective_level,
        "source_refs": record.get("source_refs", []),
        "source_language": record.get("source_language", "it"),
        "source_name": record.get("source_name", ""),
        "translation_status": record.get("translation_status", "not_required"),
        "review_status": record.get("review_status", "pending"),
        "review_notes": record.get("review_notes", ""),
        "review_reason": reference_review_reason(record),
        "review_state": review_state,
        "is_trusted": reference_is_trusted(record),
        "needs_review": review_state == "review" or record.get("ai_review_status") in {"conflict", "low_confidence"},
        "canonical_id": record.get("canonical_id"),
        "ai_review_status": record.get("ai_review_status", "pending"),
        "ai_confidence": record.get("ai_confidence", 0),
        "canonical_selected": (record.get("ai_review_corrections") or {}).get("selected"),
    }


async def private_reference_review_history(user_id: str, reference_id: str, *, db=None) -> list[dict]:
    """Load the append-only audit trail for one owner-controlled record."""
    _db = db if db is not None else _singleton_db
    collection = getattr(_db, "private_reference_review_history", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Cronologia revisioni non disponibile: applica prima la migrazione SQL")
    try:
        return await collection.find(
            {"user_id": user_id, "reference_id": reference_id}
        ).sort("reviewed_at", -1).sort("id", -1).to_list(500)
    except Exception as exc:
        if "private_reference_review_history" in str(exc):
            raise HTTPException(
                status_code=503,
                detail="Cronologia revisioni non disponibile: applica prima la migrazione SQL",
            ) from exc
        raise


async def reference_review_details(record: dict, *, db=None) -> dict:
    """Return the private side-by-side material needed to review one record."""
    summary = reference_summary(record)
    source_language = record.get("source_language", "it")
    original = {
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
    translation = {
        "name": record.get("name", ""),
        "description": record.get("description", ""),
        "full_text": record.get("full_text", ""),
        "attributes": copy.deepcopy(record.get("attributes") or {}),
    }
    return {
        **summary,
        "source_name": original["name"],
        "source_description": original["description"],
        "source_full_text": original["full_text"],
        "source_attributes": original["attributes"],
        "original": original,
        "translation": translation,
        "manual": copy.deepcopy(record.get("source_refs") or []),
        "review_history": await private_reference_review_history(record["user_id"], record["id"], db=db),
    }


def public_reference_snapshot(snapshot: dict) -> dict:
    allowed = {
        "reference_id", "name", "reference_type", "source_refs",
        "parent_class", "parent_subclass", "level",
        "source_text_checksum", "content_revision", "saved_at", "derived_attributes",
    }
    return {
        key: copy.deepcopy(value)
        for key, value in (snapshot or {}).items()
        if key in allowed
    }


def public_card_payload(card: dict) -> dict:
    """Strip raw manual extracts from every card-shaped response."""
    def redact(value):
        if isinstance(value, list):
            return [redact(item) for item in value]
        if not isinstance(value, dict):
            return value
        if value.get("reference_id") and any(
            key in value for key in ("source_text_checksum", "content_revision", "saved_at")
        ):
            return public_reference_snapshot(value)
        return {
            key: redact(item)
            for key, item in value.items()
            if key not in {"full_text", "source_full_text", "source_description", "source_attributes"}
        }
    return redact(copy.deepcopy(card))


def public_reference_update(update: dict) -> dict:
    result = public_card_payload(update)
    for key in ("before", "after"):
        if result.get(key):
            result[key] = public_reference_snapshot(result[key])
    return result


def card_response(card: dict):
    from schemas.cards import Card
    return Card(**public_card_payload(card))


def manual_coverage_report(records: list[dict]) -> list[dict]:
    report: list[dict] = []
    for filename in available_reference_manuals():
        categories = MANUAL_COVERAGE_CATEGORIES.get(filename, tuple(REFERENCE_TYPES))
        source_records = [
            record for record in records
            if any(ref.get("filename") == filename for ref in record.get("source_refs", []))
        ]
        coverage = []
        for reference_type in categories:
            category_records = [
                record for record in source_records
                if reference_effective_type(record) == reference_type
            ]
            valid = sum(reference_is_trusted(record) for record in category_records)
            to_review = sum(reference_review_state(record) == "review" for record in category_records)
            coverage.append({
                "reference_type": reference_type,
                "valid": valid,
                "to_review": to_review,
                "missing": int(not category_records),
                "records_total": len(category_records),
            })
        report.append({
            "filename": filename,
            "title": manual_source_metadata(filename)["title"],
            "source_language": manual_source_language(filename),
            "categories": coverage,
        })
    return report


def manual_import_progress(filename: str, records: list[dict], page_count: Optional[int]) -> dict:
    source_records = [
        record for record in records
        if any(ref.get("filename") == filename for ref in record.get("source_refs", []))
    ]
    imported_pages = sorted({
        ref.get("page")
        for record in source_records
        for ref in record.get("source_refs", [])
        if ref.get("filename") == filename and isinstance(ref.get("page"), int)
    })
    translated = sum(record.get("translation_status") == "translated" for record in source_records)
    failed = sum(record.get("translation_status") == "failed" for record in source_records)
    processing = sum(record.get("translation_status") == TRANSLATION_PROCESSING_STATUS for record in source_records)
    to_review = sum(reference_review_state(record) == "review" for record in source_records)
    ready = sum(reference_is_trusted(record) for record in source_records)
    translation_pending = failed + processing + sum(
        record.get("source_language") == "es"
        and record.get("translation_status", "not_required") not in {"translated", "failed", TRANSLATION_PROCESSING_STATUS}
        for record in source_records
    )
    translation_total = translated + translation_pending
    records_translation_pending = sum(
        record.get("translation_status") == "failed"
        and record.get("translation_error") in {"provider_rate_limited", "provider_rate_limited_exhausted"}
        and not reference_is_trusted(record)
        for record in source_records
    )
    records_translation_failed = sum(
        record.get("translation_status") == "failed"
        and record.get("translation_error") not in {None, "", "provider_rate_limited", "provider_rate_limited_exhausted"}
        and not reference_is_trusted(record)
        for record in source_records
    )
    return {
        "records_total": len(source_records),
        "records_ready": ready,
        "records_translated": translated,
        "records_to_review": to_review,
        "records_failed": failed,
        "records_processing": processing,
        "translation_total": translation_total,
        "translation_progress": round((translated / translation_total) * 100) if translation_total else 0,
        "imported_pages": imported_pages,
        "pages_with_records": len(imported_pages),
        "page_progress": round((len(imported_pages) / page_count) * 100) if page_count else 0,
        "records_translation_pending": records_translation_pending,
        "records_translation_failed": records_translation_failed,
    }


def _translation_lease_is_active(record: dict) -> bool:
    return (
        record.get("translation_status") == TRANSLATION_PROCESSING_STATUS
        and int(record.get("translation_lease_expires_at") or 0) > int(time.time())
    )


async def _wait_for_translation(collection: Any, user_id: str, reference_id: str, fallback: dict) -> dict:
    lease_remaining = max(
        0,
        int(fallback.get("translation_lease_expires_at") or 0) - int(time.time()),
    )
    deadline = asyncio.get_running_loop().time() + min(TRANSLATION_WAIT_SECONDS, lease_remaining)
    current = fallback
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(TRANSLATION_POLL_INTERVAL_SECONDS)
        current = await collection.find_one({"id": reference_id, "user_id": user_id})
        if not current or current.get("translation_status") != TRANSLATION_PROCESSING_STATUS:
            return current or fallback
    return current or fallback


async def retry_private_reference_translation(user_id: str, reference_id: str, *, db=None) -> dict:
    """Retry one failed Spanish translation without re-reading the manual."""
    _db = db if db is not None else _singleton_db
    collection = getattr(_db, "private_reference_records", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Biblioteca privata non disponibile: applica prima la migrazione SQL")

    record = await collection.find_one({"id": reference_id, "user_id": user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    if record.get("source_language") != "es":
        raise HTTPException(status_code=400, detail="Questo record non richiede una traduzione dallo spagnolo")
    if record.get("translation_status") != "failed" and _translation_lease_is_active(record):
        return await _wait_for_translation(collection, user_id, reference_id, record)
    if record.get("translation_status") != "failed":
        if record.get("translation_status") != TRANSLATION_PROCESSING_STATUS:
            return record

    if record.get("review_status") == "verified":
        return record

    now = int(time.time())
    lease_id = uuid.uuid4().hex
    claim = await collection.update_one(
        {
            "id": reference_id,
            "user_id": user_id,
            "review_status": {"$ne": "verified"},
            "$or": [
                {"translation_status": "failed"},
                {
                    "translation_status": TRANSLATION_PROCESSING_STATUS,
                    "translation_lease_expires_at": {"$lt": now + 1},
                },
            ],
        },
        {
            "$set": {
                "translation_status": TRANSLATION_PROCESSING_STATUS,
                "translation_error": "",
                "translation_lease_id": lease_id,
                "translation_lease_expires_at": now + TRANSLATION_LEASE_SECONDS,
                "updated_at": utc_now(),
            }
        },
    )
    if not claim or not getattr(claim, "matched_count", 0):
        current = await collection.find_one({"id": reference_id, "user_id": user_id})
        if current and current.get("translation_status") == TRANSLATION_PROCESSING_STATUS:
            return await _wait_for_translation(collection, user_id, reference_id, current)
        return current or record

    record = await collection.find_one({"id": reference_id, "user_id": user_id}) or record

    source_record = {
        "id": reference_id,
        "source_name": record.get("source_name", ""),
        "source_description": record.get("source_description", ""),
        "source_full_text": record.get("source_full_text", ""),
        "source_attributes": dict(record.get("source_attributes") or {}),
    }
    try:
        translated, error = await asyncio.to_thread(translate_spanish_reference_batch, [source_record])
    except Exception as exc:
        logger.warning("Retry della traduzione Gemini fallito per %s: %s", reference_id, exc)
        translated, error = {}, "provider_translation_failed"

    translated_record = translated.get(reference_id)
    processing_query = {
        "id": reference_id,
        "user_id": user_id,
        "translation_status": TRANSLATION_PROCESSING_STATUS,
        "translation_lease_id": lease_id,
        "review_status": {"$ne": "verified"},
    }
    if not translated_record:
        final_error = error or "provider_translation_failed"
        if final_error == "provider_rate_limited":
            await collection.update_one(
                processing_query,
                {"$set": {
                    "translation_status": "failed",
                    "translation_error": "provider_rate_limited",
                    "translation_lease_id": "",
                    "translation_lease_expires_at": 0,
                    "updated_at": utc_now(),
                }},
            )
        else:
            await collection.update_one(
                processing_query,
                {"$set": {
                    "review_flags": sorted(set(record.get("review_flags") or []) | {"traduzione_da_verificare"}),
                    "review_status": "needs_review",
                    "translation_status": "failed",
                    "translation_error": final_error,
                    "translation_lease_id": "",
                    "translation_lease_expires_at": 0,
                    "updated_at": utc_now(),
                }},
            )
        return await collection.find_one({"id": reference_id, "user_id": user_id}) or record

    remaining_review_flags = sorted(
        set(record.get("review_flags") or []) - {"traduzione_da_verificare"}
    )
    await collection.update_one(
        processing_query,
        {"$set": {
            "name": translated_record["name"],
            "normalized_name": normalize_reference_name(translated_record["name"]),
            "description": translated_record["description"],
            "full_text": translated_record["full_text"],
            "attributes": translated_record["attributes"],
            "translation_status": "translated",
            "translation_error": "",
            "translation_lease_id": "",
            "translation_lease_expires_at": 0,
            "review_flags": remaining_review_flags,
            "review_status": "needs_review" if remaining_review_flags else "pending",
            "updated_at": utc_now(),
        }},
    )
    return await collection.find_one({"id": reference_id, "user_id": user_id}) or record
