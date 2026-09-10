#!/usr/bin/env python3
"""Read-only audit of columns named in historical PostgREST schema-cache failures.

The audit only summarizes failed import-job error classes. It never retries jobs,
writes to Supabase, changes review state, performs OCR/translation, or authorizes
canonicalization. Named database columns are emitted only as aggregate counters so
operators can compare historical failures with the live schema before considering
any recovery action.
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

from scripts.audit_manual_import_readiness import _is_schema_cache_failure, fetch_all

_MISSING_COLUMN_RE = re.compile(
    r"could not find the ['\"](?P<column>[^'\"]+)['\"] column of ['\"][^'\"]+['\"] in the schema cache",
    re.IGNORECASE,
)


def _missing_schema_cache_column(job: dict) -> str:
    """Return the named missing column or ``unknown`` for generic cache failures."""
    if not _is_schema_cache_failure(job):
        return ""
    match = _MISSING_COLUMN_RE.search(str(job.get("last_error") or ""))
    return match.group("column").strip().lower() if match else "unknown"


def summarize_schema_cache_failure_columns(jobs: list[dict]) -> dict[str, Any]:
    failed = [job for job in jobs if str(job.get("status") or "").strip().lower() == "failed"]
    schema_failures = [job for job in failed if _is_schema_cache_failure(job)]
    columns = Counter(_missing_schema_cache_column(job) for job in schema_failures)

    return {
        "failed_jobs_total": len(failed),
        "schema_cache_failures_total": len(schema_failures),
        "schema_cache_missing_column_breakdown": dict(sorted(columns.items())),
        "requires_live_schema_recheck_before_recovery": len(schema_failures) > 0,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "review_state_mutation_authorized": False,
        "ocr_generation_authorized": False,
        "translation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs = await fetch_all(db.private_manual_import_jobs)
    print(json.dumps(summarize_schema_cache_failure_columns(jobs), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache failure-column audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
