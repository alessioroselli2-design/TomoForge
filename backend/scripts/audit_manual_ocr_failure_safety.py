#!/usr/bin/env python3
"""Read-only safety audit for failed manual imports with OCR backlog.

The audit reports only aggregate counts. It never exposes filenames, page
numbers, error payloads, source contents, or performs database writes. Passing
this audit never authorizes OCR or an import retry; it only identifies whether
an OCR-blocked failure is pristine enough for further read-only investigation.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import (
    _has_ocr_backlog,
    _has_record_activity,
    _was_retried,
    fetch_all,
)


def summarize_ocr_failure_safety(jobs: list[dict]) -> dict[str, Any]:
    """Return coarse safety signals for failed jobs that still require OCR."""
    failed_with_ocr = [
        job
        for job in jobs
        if str(job.get("status") or "unknown") == "failed" and _has_ocr_backlog(job)
    ]
    with_activity = [job for job in failed_with_ocr if _has_record_activity(job)]
    retried = [job for job in failed_with_ocr if _was_retried(job)]
    pristine = [
        job
        for job in failed_with_ocr
        if not _has_record_activity(job) and not _was_retried(job)
    ]

    return {
        "failed_jobs_with_ocr_backlog": len(failed_with_ocr),
        "failed_ocr_jobs_with_record_activity": len(with_activity),
        "failed_ocr_jobs_retried": len(retried),
        "failed_ocr_jobs_pristine_for_read_only_investigation": len(pristine),
        "automatic_retry_authorized": False,
        "ocr_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs = await fetch_all(db.private_manual_import_jobs)
    print(json.dumps(summarize_ocr_failure_safety(jobs), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Manual OCR failure safety audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
