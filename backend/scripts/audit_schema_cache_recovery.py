#!/usr/bin/env python3
"""Read-only audit for historical PGRST204 import failures.

The audit checks whether a column previously reported missing from PostgREST's
schema cache is present in the columns currently returned by reference-record
rows. Presence is diagnostic only: partial jobs are never authorized for retry,
writeback, OCR, translation, or canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all


_MISSING_COLUMN_PATTERNS = (
    re.compile(r"could not find the ['\"](?P<column>[a-zA-Z_][a-zA-Z0-9_]*)['\"] column", re.I),
    re.compile(r"could not find the (?P<column>[a-zA-Z_][a-zA-Z0-9_]*) column", re.I),
)


def _missing_column(error: str) -> str | None:
    text = str(error or "")
    if "pgrst204" not in text.lower() or "schema cache" not in text.lower():
        return None
    for pattern in _MISSING_COLUMN_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group("column").lower()
    return None


def _has_record_activity(job: dict[str, Any]) -> bool:
    return any(
        isinstance(job.get(field), (int, float)) and job.get(field, 0) > 0
        for field in ("records_imported", "records_updated", "records_flagged", "records_skipped")
    )


def _was_retried(job: dict[str, Any]) -> bool:
    attempts = job.get("attempt_count")
    return isinstance(attempts, (int, float)) and attempts > 1


def _current_record_columns(records: list[dict[str, Any]]) -> set[str]:
    columns: set[str] = set()
    for row in records:
        columns.update(str(key).lower() for key in row.keys())
    return columns


def summarize_schema_cache_recovery(
    jobs: list[dict[str, Any]], records: list[dict[str, Any]]
) -> dict[str, Any]:
    columns = _current_record_columns(records)
    failed = [job for job in jobs if str(job.get("status") or "") == "failed"]
    schema_jobs = []
    for job in failed:
        column = _missing_column(str(job.get("last_error") or ""))
        if column:
            schema_jobs.append((job, column))

    now_present = [(job, column) for job, column in schema_jobs if column in columns]
    still_absent = [(job, column) for job, column in schema_jobs if column not in columns]
    now_present_partial = [(job, column) for job, column in now_present if _has_record_activity(job)]
    now_present_partial_retried = [
        (job, column) for job, column in now_present_partial if _was_retried(job)
    ]

    return {
        "failed_schema_cache_jobs": len(schema_jobs),
        "failed_schema_cache_columns_now_present": len(now_present),
        "failed_schema_cache_columns_still_absent": len(still_absent),
        "now_present_with_record_activity": len(now_present_partial),
        "now_present_without_record_activity": sum(not _has_record_activity(job) for job, _ in now_present),
        "now_present_with_record_activity_and_prior_retry": len(now_present_partial_retried),
        "now_present_partial_jobs_requiring_manual_reconciliation": len(now_present_partial),
        "live_record_columns_observed": len(columns),
        "historical_failure_may_be_stale": bool(now_present),
        "partial_retried_failure_is_review_only": bool(now_present_partial_retried),
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "ocr_generation_authorized": False,
        "translation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs, records = await asyncio.gather(
        fetch_all(db.private_manual_import_jobs),
        fetch_all(db.private_reference_records),
    )
    print(json.dumps(summarize_schema_cache_recovery(jobs, records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema cache recovery audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
