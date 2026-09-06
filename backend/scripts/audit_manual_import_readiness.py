#!/usr/bin/env python3
"""Read-only aggregate audit for structured manual import jobs.

Reports only coarse job-state counts. It never exposes filenames, errors, user
identifiers, source contents, or performs database writes.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


async def fetch_all(collection: Any, page_size: int = 1000) -> list[dict]:
    """Read all jobs in bounded pages so row limits cannot truncate the audit."""
    rows: list[dict] = []
    offset = 0
    while True:
        page = await collection.find({}).to_list(page_size, offset=offset)
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += len(page)


def _has_record_activity(job: dict) -> bool:
    """Return whether a failed job reports any record-level work before failure."""
    for field in ("records_imported", "records_updated", "records_flagged", "records_skipped"):
        value = job.get(field)
        if isinstance(value, (int, float)) and value > 0:
            return True
    return False


def _has_ocr_backlog(job: dict) -> bool:
    """Return whether a job records one or more pages still needing OCR."""
    pages = job.get("pages_needing_ocr")
    return isinstance(pages, list) and len(pages) > 0


def _is_schema_cache_failure(job: dict) -> bool:
    """Recognize PostgREST schema-cache misses without exposing error contents."""
    error = str(job.get("last_error") or "").lower()
    return "pgrst204" in error and "schema cache" in error


def _is_schema_cache_retry_candidate(job: dict) -> bool:
    """Return whether a schema-cache failure is safe enough to inspect for one-job retry.

    This is intentionally conservative: jobs with OCR backlog or any recorded
    record activity are excluded so the audit cannot encourage a retry that may
    duplicate or compound partial work.
    """
    return (
        _is_schema_cache_failure(job)
        and not _has_ocr_backlog(job)
        and not _has_record_activity(job)
    )


def summarize_import_readiness(jobs: list[dict]) -> dict[str, Any]:
    """Return aggregate structured-import readiness without leaking job details."""
    statuses = Counter(str(job.get("status") or "unknown") for job in jobs)
    failed = [job for job in jobs if str(job.get("status") or "unknown") == "failed"]
    failed_without_ocr_backlog = [job for job in failed if not _has_ocr_backlog(job)]
    completed = statuses["completed"]
    total = len(jobs)

    return {
        "jobs_total": total,
        "job_status_breakdown": dict(sorted(statuses.items())),
        "jobs_completed": completed,
        "jobs_failed": statuses["failed"],
        "jobs_incomplete": total - completed,
        "failed_jobs_with_record_activity": sum(_has_record_activity(job) for job in failed),
        "failed_jobs_with_ocr_backlog": sum(_has_ocr_backlog(job) for job in failed),
        "failed_jobs_without_ocr_backlog": len(failed_without_ocr_backlog),
        "failed_jobs_schema_cache_miss": sum(_is_schema_cache_failure(job) for job in failed),
        "failed_jobs_schema_cache_miss_without_ocr_backlog": sum(
            _is_schema_cache_failure(job) for job in failed_without_ocr_backlog
        ),
        "failed_jobs_schema_cache_retry_candidates": sum(
            _is_schema_cache_retry_candidate(job) for job in failed
        ),
        "failed_jobs_retried": sum(
            isinstance(job.get("attempt_count"), (int, float)) and job.get("attempt_count") > 1
            for job in failed
        ),
        "failed_jobs_retried_without_ocr_backlog": sum(
            isinstance(job.get("attempt_count"), (int, float)) and job.get("attempt_count") > 1
            for job in failed_without_ocr_backlog
        ),
        "failed_jobs_external_processing_confirmed": sum(
            job.get("external_processing_confirmed") is True for job in failed
        ),
        "failed_jobs_translation_processing_confirmed": sum(
            job.get("translation_processing_confirmed") is True for job in failed
        ),
        "structured_import_stable": total > 0 and statuses["failed"] == 0 and completed == total,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs = await fetch_all(db.private_manual_import_jobs)
    print(json.dumps(summarize_import_readiness(jobs), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Manual import readiness audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
