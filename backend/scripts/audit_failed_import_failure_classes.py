#!/usr/bin/env python3
"""Read-only classification of failed structured manual import jobs.

The audit separates known failure classes without exposing filenames, source
contents, or error payloads. It also makes the recovery gate explicit: every
failed job requires reconciliation before any retry can be considered. It never
authorizes database writes, OCR, translation, canonicalization, or automatic
retry.
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

from scripts.audit_manual_import_readiness import (
    _has_ocr_backlog,
    _has_record_activity,
    _is_manual_source_duplicate_failure,
    _is_non_schema_investigation_candidate,
    _is_schema_cache_failure,
    _is_schema_cache_retry_candidate,
    fetch_all,
)


def _is_manual_source_missing_failure(job: dict) -> bool:
    error = str(job.get("last_error") or "").strip().lower()
    return error == "manual_source_missing"


def _failure_class(job: dict) -> str:
    if _is_schema_cache_failure(job):
        return "schema_cache"
    if _is_manual_source_duplicate_failure(job):
        return "manual_source_duplicate"
    if _is_manual_source_missing_failure(job):
        return "manual_source_missing"
    return "other"


def _is_known_provenance_failure(job: dict) -> bool:
    return _is_manual_source_duplicate_failure(job) or _is_manual_source_missing_failure(job)


def summarize_failed_import_failure_classes(jobs: list[dict]) -> dict[str, Any]:
    failed = [job for job in jobs if str(job.get("status") or "") == "failed"]
    classes = Counter(_failure_class(job) for job in failed)
    missing = [job for job in failed if _is_manual_source_missing_failure(job)]
    zero_activity = [job for job in failed if not _has_record_activity(job)]

    return {
        "failed_jobs_total": len(failed),
        "failure_class_breakdown": dict(sorted(classes.items())),
        "failed_jobs_with_record_activity": sum(_has_record_activity(job) for job in failed),
        "failed_jobs_zero_activity": len(zero_activity),
        "zero_activity_known_provenance_failures": sum(
            _is_known_provenance_failure(job) for job in zero_activity
        ),
        "zero_activity_unclassified_failures": sum(
            _failure_class(job) == "other" for job in zero_activity
        ),
        "failed_jobs_with_ocr_backlog": sum(_has_ocr_backlog(job) for job in failed),
        "schema_cache_retry_candidates": sum(_is_schema_cache_retry_candidate(job) for job in failed),
        "manual_source_missing_jobs": len(missing),
        "manual_source_missing_investigation_candidates": sum(
            _is_non_schema_investigation_candidate(job) for job in missing
        ),
        "manual_reconciliation_required": len(failed),
        "safe_automatic_retry_candidates": 0,
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

    jobs = await fetch_all(db.private_manual_import_jobs)
    print(json.dumps(summarize_failed_import_failure_classes(jobs), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Failed import failure-class audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
