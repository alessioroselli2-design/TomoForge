#!/usr/bin/env python3
"""Read-only completeness gate for schema-cache import failures.

This audit deliberately does not infer completeness from provenance alone. A
failed schema-cache job is considered *completion-eligible for review* only when
its recorded page progress reaches the declared page count, it has no OCR
backlog, and records exist with the exact job source_key. Even then the audit
never authorizes retry, database writes, or canonicalization.
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


def _page_progress_complete(job: dict) -> bool:
    current_page = job.get("current_page")
    page_count = job.get("page_count")
    return (
        isinstance(current_page, int)
        and isinstance(page_count, int)
        and page_count > 0
        and current_page >= page_count
    )


def summarize_schema_cache_record_completeness(
    jobs: list[dict], records: list[dict]
) -> dict[str, Any]:
    failed_with_activity = [
        job
        for job in jobs
        if str(job.get("status") or "unknown") == "failed"
        and _is_schema_cache_failure(job)
        and _has_record_activity(job)
    ]

    record_counts_by_source_key: dict[str, int] = {}
    for record in records:
        source_key = str(record.get("source_key") or "").strip()
        if source_key:
            record_counts_by_source_key[source_key] = (
                record_counts_by_source_key.get(source_key, 0) + 1
            )

    with_exact_record_provenance = 0
    with_page_progress_complete = 0
    without_ocr_backlog = 0
    completion_review_candidates = 0

    for job in failed_with_activity:
        filename = str(job.get("filename") or "").strip()
        has_exact_records = bool(filename) and record_counts_by_source_key.get(filename, 0) > 0
        page_complete = _page_progress_complete(job)
        no_ocr_backlog = not _has_ocr_backlog(job)

        with_exact_record_provenance += int(has_exact_records)
        with_page_progress_complete += int(page_complete)
        without_ocr_backlog += int(no_ocr_backlog)
        completion_review_candidates += int(
            has_exact_records and page_complete and no_ocr_backlog
        )

    total = len(failed_with_activity)
    return {
        "schema_cache_failures_with_record_activity": total,
        "with_exact_record_source_key_provenance": with_exact_record_provenance,
        "with_page_progress_reaching_declared_end": with_page_progress_complete,
        "without_ocr_backlog": without_ocr_backlog,
        "completion_review_candidates": completion_review_candidates,
        "record_set_completeness_confirmed": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs = await fetch_all(db.private_manual_import_jobs)
    records = await fetch_all(db.private_reference_records)
    print(
        json.dumps(
            summarize_schema_cache_record_completeness(jobs, records),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache completeness audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
