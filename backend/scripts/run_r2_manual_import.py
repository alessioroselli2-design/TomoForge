#!/usr/bin/env python3
"""R2 import entry point with safe OCR fallback for recovered private manuals.

The web app keeps its conservative request path unchanged. This long-running
worker can recover a broken native text layer page-by-page and gives spell-card
pages a deterministic transcription layout that the existing reference parser
can understand. Spanish text-native sources retain their no-OCR policy.
"""

from __future__ import annotations

import asyncio
import base64
import sys
from hashlib import sha256
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


SPELL_CARD_SOURCES = frozenset({
    "Bardo .pdf",
    "Chierico.pdf",
    "Druido .pdf",
    "Mago .pdf",
    "Paladino .pdf",
    "Ranger .pdf",
    "Stregone .pdf",
    "Warlock .pdf",
})
SPELL_CARD_PARSER_REVISION = "r2-spell-card-ocr-v1"


def _worker_openai_ocr(page, page_number: int, source_language: str = "") -> str:
    """Transcribe a page, normalising spell-card grids without inventing facts."""
    from services import library

    if not library.OPENAI_API_KEY:
        library.logger.warning("OCR OpenAI non configurato: OPENAI_API_KEY mancante")
        return ""

    import pymupdf as fitz

    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.45, 1.45), alpha=False)
    image_b64 = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
    language_hint = (
        f" La lingua dichiarata della fonte è {source_language}."
        if source_language else ""
    )
    prompt = (
        "Trascrivi fedelmente la pagina nella sua lingua originale; non tradurre."
        f"{language_hint} Non riassumere, non inventare testo e non aggiungere commenti. "
        "Se la pagina contiene una griglia di carte incantesimo, trascrivi OGNI carta "
        "separatamente e senza Markdown. Per ciascuna carta usa esattamente questo ordine: "
        "prima riga TITOLO DELL'INCANTESIMO in maiuscolo; seconda riga, per un incantesimo "
        "di livello 1 o superiore, '<Scuola> di <N>° livello', oppure per un trucchetto "
        "'Trucchetto di <Scuola>'; poi 'Tempo di Lancio: ...', 'Gittata: ...', "
        "'Componenti: ...', 'Durata: ...'; infine il testo completo dell'effetto. "
        "Ricava scuola e livello esclusivamente dalla carta, anche quando sono stampati in "
        "fondo, e spostali nella seconda riga senza modificarli. Se una carta continua in "
        "un'altra carta o colonna, mantieni tutto il testo visibile e non completare parti "
        "mancanti. Lascia una riga vuota tra una carta e la successiva. "
        "Se la pagina NON contiene carte incantesimo, mantieni titoli, paragrafi e tabelle "
        "leggibili come nel documento. Restituisci solo la trascrizione."
    )

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {library.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": library.OPENAI_OCR_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high",
                        }},
                    ],
                }],
                "temperature": 0,
                "max_tokens": 4096,
            },
            timeout=(15, 180),
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        library.logger.warning(
            "OCR OpenAI non disponibile per pagina %s (HTTP %s)",
            page_number,
            status_code or "errore",
        )
        return ""
    except requests.RequestException as exc:
        library.logger.warning(
            "OCR OpenAI non raggiungibile per pagina %s: %s",
            page_number,
            exc,
        )
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
            letters = sum(char.isalpha() for char in transcription)
            printable = sum(char.isprintable() for char in transcription)
            library.logger.info(
                "OCR OpenAI pagina %s: len=%d alpha=%.0f%% printable=%.0f%%",
                page_number,
                len(transcription),
                100 * letters / max(len(transcription), 1),
                100 * printable / max(len(transcription), 1),
            )
            return transcription
        library.logger.warning("OCR OpenAI senza testo per pagina %s", page_number)
    except (ValueError, TypeError, IndexError, AttributeError) as exc:
        library.logger.warning(
            "OCR OpenAI ha restituito una risposta non leggibile per pagina %s: %s",
            page_number,
            exc,
        )
    return ""


def enable_worker_ocr_fallback() -> None:
    """Allow OpenAI OCR fallback for non-Spanish pages in the R2 worker only."""
    from services import library

    if getattr(library, "_r2_ocr_fallback_enabled", False):
        return

    native_requires_ocr = library.manual_requires_ocr
    source_language = library.manual_source_language

    def worker_requires_ocr(filename: str) -> bool:
        return native_requires_ocr(filename) or source_language(filename) != "es"

    library.manual_requires_ocr = worker_requires_ocr
    library.openai_ocr_manual_page = _worker_openai_ocr
    library._r2_ocr_fallback_enabled = True


def enable_worker_parser_revision() -> None:
    """Force one clean re-index when the spell-card transcription format changes."""
    from reference_sources import canonical_physical_filename
    from services import library

    if getattr(library, "_r2_parser_revision_enabled", False):
        return

    native_fingerprint = library.manual_source_fingerprint

    def worker_fingerprint(path: Path) -> str:
        value = native_fingerprint(path)
        canonical = canonical_physical_filename(path.name)
        if canonical in SPELL_CARD_SOURCES:
            return sha256(
                f"{value}:{SPELL_CARD_PARSER_REVISION}".encode("utf-8")
            ).hexdigest()
        return value

    library.manual_source_fingerprint = worker_fingerprint
    library._r2_parser_revision_enabled = True


async def _cleanup_stale_ocr_artifacts(worker, requested_filename: str) -> int:
    """Remove only source-local OCR artefacts before a targeted corrected re-index."""
    from core.db import db

    user_id = await worker._owner_id(db)
    canonical = worker._canonical_filename(requested_filename)
    _imported, jobs = await worker._existing_source_state(db, user_id)
    job_state = jobs.get(canonical)
    if not job_state:
        return 0

    filename = job_state["filename"]
    rows = await db.private_reference_records.find(
        {"user_id": user_id, "source_key": filename}
    ).to_list(2000)

    removed = 0
    for row in rows:
        flags = {str(flag) for flag in (row.get("review_flags") or [])}
        refs = list(row.get("source_refs") or [])
        ref_sources = {
            worker._canonical_filename(str(ref.get("filename") or ""))
            for ref in refs
            if ref.get("filename")
        }
        source_local = bool(ref_sources) and ref_sources == {canonical}
        if "ocr_da_verificare" not in flags or not source_local:
            continue
        result = await db.private_reference_records.delete_one(
            {"id": row["id"], "user_id": user_id}
        )
        removed += int(result.deleted_count or 0)

    if removed:
        print(f"Removed {removed} stale source-local OCR artefact(s) for {filename}.")
    return removed


async def _reset_false_success_for_explicit_retry(worker, requested_filename: str) -> None:
    """Restart an explicit retry that previously completed with only OCR misses."""
    from core.db import db

    user_id = await worker._owner_id(db)
    canonical = worker._canonical_filename(requested_filename)
    _imported, jobs = await worker._existing_source_state(db, user_id)
    job_state = jobs.get(canonical)
    if not job_state:
        return

    filename = job_state["filename"]
    job = await db.private_manual_import_jobs.find_one(
        {"user_id": user_id, "filename": filename}
    )
    if not job or str(job.get("status") or "") != "completed":
        return

    persisted = int(job.get("records_imported") or 0) + int(job.get("records_updated") or 0)
    unresolved = list(job.get("pages_needing_ocr") or [])
    if persisted > 0 or not unresolved:
        return

    await db.private_manual_import_jobs.update_one(
        {"id": job["id"], "user_id": user_id, "status": "completed"},
        {"$set": {
            "status": "queued",
            "current_page": 1,
            "attempt_count": 0,
            "last_error": "",
            "pages_needing_ocr": [],
            "records_imported": 0,
            "records_updated": 0,
            "records_flagged": 0,
            "records_skipped": 0,
            "lease_id": "",
            "lease_expires_at": 0,
            "completed_at": None,
        }},
    )
    print(f"Resetting prior zero-record OCR-only completion for {filename}.")


async def _verify_requested_import(worker, requested_filename: str) -> None:
    """Reject a false-success job that completed without producing any records."""
    from core.db import db

    user_id = await worker._owner_id(db)
    canonical = worker._canonical_filename(requested_filename)
    _imported, jobs = await worker._existing_source_state(db, user_id)
    job_state = jobs.get(canonical)
    if not job_state:
        raise RuntimeError(f"No durable import job found for {requested_filename}")

    filename = job_state["filename"]
    job = await db.private_manual_import_jobs.find_one(
        {"user_id": user_id, "filename": filename}
    )
    if not job or str(job.get("status") or "") != "completed":
        raise RuntimeError(f"Import job did not complete for {filename}")

    persisted = int(job.get("records_imported") or 0) + int(job.get("records_updated") or 0)
    if persisted <= 0:
        unresolved = list(job.get("pages_needing_ocr") or [])
        raise RuntimeError(
            f"Import completed without persisted records for {filename}; "
            f"unresolved OCR pages={unresolved}"
        )


def main() -> int:
    enable_worker_ocr_fallback()
    enable_worker_parser_revision()

    from scripts import import_manuals_from_r2 as worker

    args = worker._parser().parse_args()
    if args.max_manuals < 1:
        print("--max-manuals must be at least 1", file=sys.stderr)
        return 2

    try:
        if args.filename:
            asyncio.run(_cleanup_stale_ocr_artifacts(worker, args.filename))
            asyncio.run(_reset_false_success_for_explicit_retry(worker, args.filename))
        result = asyncio.run(worker._run_import(args))
        if result == 0 and args.filename:
            asyncio.run(_verify_requested_import(worker, args.filename))
        return result
    except Exception as exc:
        print(f"R2 manual import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
