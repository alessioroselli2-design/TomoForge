#!/usr/bin/env python3
"""Read-only audit for failed schema-cache manual imports with partial activity.

Reports aggregate safety signals only. It never exposes filenames, error text,
source contents, or performs retries/writes. A reconciliation candidate is only
eligible for further read-only inspection; this script never authorizes retry.
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
    _was_retried,
    fetch_all,
)


def summarize_schema_cache_partial_activity(jobs: list[dict]) -> dict[str, Any]:
    failed_schema = [
        job for job in jobs
        if str(job.get("status") or "unknown") == "failed" and _is_schema_cache_failure(job)
    ]
    with_activity = [job for job in failed_schema if _has_record_activity(job)]
    without_ocr = [job for job in with_activity if not _has_ocr_backlog(job)]
    retried = [job for job in with_activity if _was_retried(job)]
    read_only_candidates = [
        job for job in with_activity
        if not _has_ocr_backlog(job)
    ]

    return {
        "failed_schema_cache_jobs": len(failed_schema),
        "failed_schema_cache_jobs_with_record_activity": len(with_activity),
        "failed_schema_cache_jobs_with_activity_without_ocr": len(without_ocr),
        "failed_schema_cache_jobs_with_activity_retried": len(retried),
        "failed_schema_cache_jobs_for_read_only_reconciliation": len(read_only_candidates),
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs = await fetch_all(db.private_manual_import_jobs)
    print(json.dumps(summarize_schema_cache_partial_activity(jobs), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache partial activity audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
