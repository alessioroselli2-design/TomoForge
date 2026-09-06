#!/usr/bin/env python3
"""Read-only audit for schema-cache failures against registered source identity.

Reports aggregate linkage signals only. It never exposes filenames, fingerprints,
source contents, errors, or performs retries/writes. Exact fingerprint linkage is
only a reconciliation signal and never authorizes mutation.
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
    _has_record_activity,
    _is_schema_cache_failure,
    fetch_all,
)


def summarize_schema_cache_source_links(jobs: list[dict], sources: list[dict]) -> dict[str, Any]:
    failed_schema = [
        job for job in jobs
        if str(job.get("status") or "unknown") == "failed" and _is_schema_cache_failure(job)
    ]
    source_by_fingerprint: dict[str, list[dict]] = {}
    for source in sources:
        fingerprint = str(source.get("physical_sha256") or "").strip()
        if fingerprint:
            source_by_fingerprint.setdefault(fingerprint, []).append(source)

    with_activity = [job for job in failed_schema if _has_record_activity(job)]
    exact_matches = []
    exact_active_single_logical = []
    unmatched = []

    for job in with_activity:
        fingerprint = str(job.get("source_fingerprint") or "").strip()
        matches = source_by_fingerprint.get(fingerprint, []) if fingerprint else []
        if not matches:
            unmatched.append(job)
            continue
        exact_matches.append(job)
        logical_ids = {
            str(source.get("logical_source_id") or "")
            for source in matches if source.get("logical_source_id")
        }
        has_active = any(str(source.get("source_status") or "") == "active" for source in matches)
        if len(logical_ids) == 1 and has_active:
            exact_active_single_logical.append(job)

    return {
        "failed_schema_cache_jobs": len(failed_schema),
        "failed_schema_cache_jobs_with_record_activity": len(with_activity),
        "with_exact_registered_source_fingerprint": len(exact_matches),
        "with_exact_active_single_logical_source": len(exact_active_single_logical),
        "without_exact_registered_source_fingerprint": len(unmatched),
        "fingerprint_reconciliation_complete": bool(with_activity) and not unmatched,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs = await fetch_all(db.private_manual_import_jobs)
    sources = await fetch_all(db.private_reference_sources)
    print(json.dumps(summarize_schema_cache_source_links(jobs, sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache source-link audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
