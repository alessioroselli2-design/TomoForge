#!/usr/bin/env python3
"""Read-only logical provenance audit for schema-cache import failures.

The audit uses exact record source_key provenance plus a conservative normalized
filename match to the source registry. It reports aggregate signals only, never
exposes private names/content/errors, and never authorizes retry or database
writes. A reconciled logical identity does not prove that a partial import is
complete.
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

from scripts.audit_manual_import_readiness import (
    _has_record_activity,
    _is_schema_cache_failure,
    fetch_all,
)

_TIMESTAMP_SUFFIX = re.compile(r"(?:[_-]+)\d{10,}$")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _normalized_source_name(value: object) -> str:
    name = Path(str(value or "").strip()).name.lower()
    if name.endswith(".pdf"):
        name = name[:-4]
    name = _TIMESTAMP_SUFFIX.sub("", name)
    return " ".join(part for part in _NON_ALNUM.split(name) if part)


def summarize_schema_cache_logical_provenance(
    jobs: list[dict], sources: list[dict], records: list[dict]
) -> dict[str, Any]:
    failed_with_activity = [
        job
        for job in jobs
        if str(job.get("status") or "unknown") == "failed"
        and _is_schema_cache_failure(job)
        and _has_record_activity(job)
    ]

    source_groups: dict[str, list[dict]] = {}
    for source in sources:
        key = _normalized_source_name(source.get("physical_filename"))
        if key:
            source_groups.setdefault(key, []).append(source)

    record_counts_by_source_key: dict[str, int] = {}
    for record in records:
        key = str(record.get("source_key") or "").strip()
        if key:
            record_counts_by_source_key[key] = record_counts_by_source_key.get(key, 0) + 1

    with_exact_record_provenance = 0
    reconciled_logical_identity = 0
    ambiguous_registry_identity = 0
    unmatched_registry_identity = 0

    for job in failed_with_activity:
        filename = str(job.get("filename") or "").strip()
        if record_counts_by_source_key.get(filename, 0) <= 0:
            continue
        with_exact_record_provenance += 1

        registry_matches = source_groups.get(_normalized_source_name(filename), [])
        if not registry_matches:
            unmatched_registry_identity += 1
            continue

        logical_ids = {
            str(source.get("logical_source_id") or "").strip()
            for source in registry_matches
            if str(source.get("logical_source_id") or "").strip()
        }
        has_active = any(
            str(source.get("source_status") or "").strip() == "active"
            for source in registry_matches
        )
        if len(logical_ids) == 1 and has_active:
            reconciled_logical_identity += 1
        else:
            ambiguous_registry_identity += 1

    return {
        "schema_cache_failures_with_record_activity": len(failed_with_activity),
        "with_exact_record_source_key_provenance": with_exact_record_provenance,
        "with_reconciled_active_logical_source_identity": reconciled_logical_identity,
        "with_ambiguous_registry_identity": ambiguous_registry_identity,
        "without_registry_identity_match": unmatched_registry_identity,
        "logical_identity_reconciliation_complete": bool(failed_with_activity)
        and reconciled_logical_identity == len(failed_with_activity),
        "record_set_completeness_confirmed": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs = await fetch_all(db.private_manual_import_jobs)
    sources = await fetch_all(db.private_reference_sources)
    records = await fetch_all(db.private_reference_records)
    print(
        json.dumps(
            summarize_schema_cache_logical_provenance(jobs, sources, records),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache logical provenance audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
