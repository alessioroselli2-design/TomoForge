#!/usr/bin/env python3
"""Read-only progress-deficit audit for schema-cache import failures.

This audit identifies failed schema-cache jobs that have already produced record
activity but stopped before their declared final page. It reports only aggregate
counts and page deficits. It never authorizes retries, database writes, OCR, or
canonicalization.
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
    _is_schema_cache_failure,
    fetch_all,
)


def summarize_schema_cache_progress_deficit(jobs: list[dict]) -> dict[str, Any]:
    failed_with_activity = [
        job
        for job in jobs
        if str(job.get("status") or "unknown") == "failed"
        and _is_schema_cache_failure(job)
        and _has_record_activity(job)
    ]

    valid_declared_page_count = 0
    stopped_before_declared_end = 0
    at_or_beyond_declared_end = 0
    stopped_before_end_without_ocr_backlog = 0
    pages_remaining_total = 0

    for job in failed_with_activity:
        current_page = job.get("current_page")
        page_count = job.get("page_count")
        valid_progress = (
            isinstance(current_page, int)
            and isinstance(page_count, int)
            and page_count > 0
            and current_page >= 0
        )
        if not valid_progress:
            continue

        valid_declared_page_count += 1
        if current_page < page_count:
            stopped_before_declared_end += 1
            pages_remaining_total += page_count - current_page
            if not _has_ocr_backlog(job):
                stopped_before_end_without_ocr_backlog += 1
        else:
            at_or_beyond_declared_end += 1

    return {
        "schema_cache_failures_with_record_activity": len(failed_with_activity),
        "with_valid_declared_page_count": valid_declared_page_count,
        "stopped_before_declared_end": stopped_before_declared_end,
        "at_or_beyond_declared_end": at_or_beyond_declared_end,
        "stopped_before_end_without_ocr_backlog": stopped_before_end_without_ocr_backlog,
        "aggregate_pages_remaining": pages_remaining_total,
        "progress_deficit_requires_review": stopped_before_declared_end > 0,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "ocr_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs = await fetch_all(db.private_manual_import_jobs)
    print(json.dumps(summarize_schema_cache_progress_deficit(jobs), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache progress deficit audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
