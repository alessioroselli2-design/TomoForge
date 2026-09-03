#!/usr/bin/env python3
"""R2 import entry point with safe OCR fallback for broken native text layers.

The canonical registry can mark a PDF as text-native while a recovered physical
copy still exposes an unusable font/text layer. The normal parser already knows
how to call OCR only when native text is unusable; this runner makes that
fallback available to the long-running R2 worker without changing Vercel's
request path. Spanish text-native sources keep their existing no-OCR policy.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def enable_worker_ocr_fallback() -> None:
    """Allow OpenAI OCR only as a fallback for non-Spanish native-text pages."""
    from services import library

    if getattr(library, "_r2_ocr_fallback_enabled", False):
        return

    native_requires_ocr = library.manual_requires_ocr
    source_language = library.manual_source_language

    def worker_requires_ocr(filename: str) -> bool:
        return native_requires_ocr(filename) or source_language(filename) != "es"

    library.manual_requires_ocr = worker_requires_ocr
    library._r2_ocr_fallback_enabled = True


async def _reset_false_success_for_explicit_retry(worker, requested_filename: str) -> None:
    """Restart an explicit retry that previously completed with only OCR misses.

    The durable preload worker normally resumes from its checkpoint. A previous
    false-success can therefore sit at page_count + 1 and immediately complete
    again without re-reading any page. Reset only the narrow broken state: an
    explicitly requested completed job with zero persisted records and unresolved
    OCR pages.
    """
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

    from scripts import import_manuals_from_r2 as worker

    args = worker._parser().parse_args()
    if args.max_manuals < 1:
        print("--max-manuals must be at least 1", file=sys.stderr)
        return 2

    try:
        if args.filename:
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
