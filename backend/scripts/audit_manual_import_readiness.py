#!/usr/bin/env python3
"""Read-only aggregate audit for structured manual import jobs.

Reports only coarse job-state counts. It never exposes filenames, errors, user
identifiers, source contents, or performs database writes.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


async def fetch_all(collection: Any, page_size: int = 1000) -> list[dict]:
    """Read all rows in bounded pages so row limits cannot truncate the audit."""
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


def _is_manual_source_duplicate_failure(job: dict) -> bool:
    """Recognize the importer's explicit duplicate-source guard without leaking its payload."""
    error = str(job.get("last_error") or "").lower()
    return error.startswith("manual_source_duplicate:")


def _manual_source_duplicate_payload(job: dict) -> str:
    """Return the duplicate guard payload for internal identity matching only."""
    error = str(job.get("last_error") or "")
    if not error.lower().startswith("manual_source_duplicate:"):
        return ""
    return error.split(":", 1)[1]


def _normalize_manual_identity(filename: str) -> str:
    """Normalize upload/copy suffixes so read-only duplicate reconciliation is conservative."""
    stem = Path(str(filename or "")).stem.lower()
    stem = re.sub(r"[_\W]+", " ", stem, flags=re.UNICODE).strip()
    stem = re.sub(r"\s+\d{13}$", "", stem).strip()
    stem = re.sub(r"\s+\d+$", "", stem).strip()
    return re.sub(r"\s+", " ", stem)


def _manual_source_duplicate_reconciliation_state(job: dict, sources: list[dict]) -> str:
    """Classify duplicate guards against catalog identities without authorizing writes or retries."""
    if not _is_manual_source_duplicate_failure(job) or not _is_non_schema_investigation_candidate(job):
        return "not_candidate"

    identity = _normalize_manual_identity(_manual_source_duplicate_payload(job))
    if not identity:
        return "unmatched"

    matches = [
        source for source in sources
        if _normalize_manual_identity(str(source.get("physical_filename") or "")) == identity
    ]
    if not matches:
        return "unmatched"

    logical_ids = {str(source.get("logical_source_id") or "") for source in matches if source.get("logical_source_id")}
    has_active = any(str(source.get("source_status") or "") == "active" for source in matches)
    if len(logical_ids) == 1 and has_active:
        return "reconciled_single_logical_source"
    return "ambiguous"


def _is_duplicate_like_failure(job: dict) -> bool:
    """Recognize duplicate/idempotency-like failures without exposing error text."""
    error = str(job.get("last_error") or "").lower()
    return "duplicate" in error


def _was_retried(job: dict) -> bool:
    """Return whether the import job records more than one attempt."""
    attempts = job.get("attempt_count")
    return isinstance(attempts, (int, float)) and attempts > 1


def _is_schema_cache_retry_candidate(job: dict) -> bool:
    """Return whether a schema-cache failure is safe enough to inspect for one-job retry.

    This is intentionally conservative: jobs with OCR backlog, any recorded
    record activity, or a previous retry are excluded so the audit cannot
    encourage repeated retries that may duplicate or compound partial work.
    """
    return (
        _is_schema_cache_failure(job)
        and not _has_ocr_backlog(job)
        and not _has_record_activity(job)
        and not _was_retried(job)
    )


def _is_non_schema_investigation_candidate(job: dict) -> bool:
    """Flag a failed non-schema job for diagnosis only, never automatic retry.

    The gate excludes OCR backlog, recorded record activity, and prior retries.
    Because the failure class remains unknown, passing this gate authorizes only
    read-only investigation of the cause, not re-execution of the import.
    """
    return (
        not _is_schema_cache_failure(job)
        and not _has_ocr_backlog(job)
        and not _has_record_activity(job)
        and not _was_retried(job)
    )


def summarize_import_readiness(jobs: list[dict], sources: list[dict] | None = None) -> dict[str, Any]:
    """Return aggregate structured-import readiness without leaking job or source details."""
    sources = sources or []
    statuses = Counter(str(job.get("status") or "unknown") for job in jobs)
    failed = [job for job in jobs if str(job.get("status") or "unknown") == "failed"]
    failed_without_ocr_backlog = [job for job in failed if not _has_ocr_backlog(job)]
    completed = statuses["completed"]
    total = len(jobs)
    reconciliation_states = [
        _manual_source_duplicate_reconciliation_state(job, sources) for job in failed
        if _is_manual_source_duplicate_failure(job)
    ]

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
        "failed_jobs_non_schema_cache_without_ocr_backlog": sum(
            not _is_schema_cache_failure(job) for job in failed_without_ocr_backlog
        ),
        "failed_jobs_manual_source_duplicate": sum(
            _is_manual_source_duplicate_failure(job) for job in failed
        ),
        "failed_jobs_manual_source_duplicate_reconciliation_candidates": sum(
            _is_manual_source_duplicate_failure(job) and _is_non_schema_investigation_candidate(job)
            for job in failed
        ),
        "failed_jobs_manual_source_duplicate_reconciled": reconciliation_states.count("reconciled_single_logical_source"),
        "failed_jobs_manual_source_duplicate_ambiguous": reconciliation_states.count("ambiguous"),
        "failed_jobs_manual_source_duplicate_unmatched": reconciliation_states.count("unmatched"),
        "failed_jobs_duplicate_like": sum(_is_duplicate_like_failure(job) for job in failed),
        "failed_jobs_duplicate_like_investigation_candidates": sum(
            _is_duplicate_like_failure(job) and _is_non_schema_investigation_candidate(job)
            for job in failed
        ),
        "failed_jobs_schema_cache_retry_candidates": sum(
            _is_schema_cache_retry_candidate(job) for job in failed
        ),
        "failed_jobs_non_schema_investigation_candidates": sum(
            _is_non_schema_investigation_candidate(job) for job in failed
        ),
        "failed_jobs_retried": sum(_was_retried(job) for job in failed),
        "failed_jobs_retried_without_ocr_backlog": sum(
            _was_retried(job) for job in failed_without_ocr_backlog
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
    sources = await fetch_all(db.private_reference_sources)
    print(json.dumps(summarize_import_readiness(jobs, sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Manual import readiness audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
