#!/usr/bin/env python3
"""Read-only alternate-provenance audit for schema-cache progress gaps.

The audit asks a narrow question: for failed schema-cache jobs with record activity
that stopped before the declared final page, is there *other* record provenance
associated with the same reconciled logical source identity?

Alternate provenance is only a signal for further review. Because record rows do
not encode complete page coverage, this audit never treats alternate provenance as
proof that missing pages are covered and never authorizes retries, writes, OCR, or
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
    _has_record_activity,
    _is_schema_cache_failure,
    fetch_all,
)
from scripts.audit_schema_cache_logical_provenance import _normalized_source_name


def summarize_schema_cache_alternate_provenance(
    jobs: list[dict], sources: list[dict], records: list[dict]
) -> dict[str, Any]:
    failed_with_gap = [
        job
        for job in jobs
        if str(job.get("status") or "unknown") == "failed"
        and _is_schema_cache_failure(job)
        and _has_record_activity(job)
        and isinstance(job.get("current_page"), int)
        and isinstance(job.get("page_count"), int)
        and int(job["page_count"]) > 0
        and int(job["current_page"]) < int(job["page_count"])
    ]

    sources_by_normalized_name: dict[str, list[dict]] = {}
    sources_by_logical_id: dict[str, list[dict]] = {}
    for source in sources:
        normalized = _normalized_source_name(source.get("physical_filename"))
        if normalized:
            sources_by_normalized_name.setdefault(normalized, []).append(source)
        logical_id = str(source.get("logical_source_id") or "").strip()
        if logical_id:
            sources_by_logical_id.setdefault(logical_id, []).append(source)

    record_source_keys = {
        str(record.get("source_key") or "").strip()
        for record in records
        if str(record.get("source_key") or "").strip()
    }

    reconciled_jobs = 0
    with_alternate_registered_source = 0
    with_alternate_record_provenance = 0
    ambiguous_identity = 0

    for job in failed_with_gap:
        filename = str(job.get("filename") or "").strip()
        registry_matches = sources_by_normalized_name.get(
            _normalized_source_name(filename), []
        )
        logical_ids = {
            str(source.get("logical_source_id") or "").strip()
            for source in registry_matches
            if str(source.get("logical_source_id") or "").strip()
        }
        has_active = any(
            str(source.get("source_status") or "").strip() == "active"
            for source in registry_matches
        )
        if len(logical_ids) != 1 or not has_active:
            ambiguous_identity += 1
            continue

        reconciled_jobs += 1
        logical_id = next(iter(logical_ids))
        logical_sources = sources_by_logical_id.get(logical_id, [])
        alternate_sources = [
            source
            for source in logical_sources
            if _normalized_source_name(source.get("physical_filename"))
            != _normalized_source_name(filename)
        ]
        if alternate_sources:
            with_alternate_registered_source += 1

        alternate_normalized_names = {
            _normalized_source_name(source.get("physical_filename"))
            for source in alternate_sources
            if _normalized_source_name(source.get("physical_filename"))
        }
        has_alternate_records = any(
            _normalized_source_name(source_key) in alternate_normalized_names
            for source_key in record_source_keys
            if source_key != filename
        )
        if has_alternate_records:
            with_alternate_record_provenance += 1

    return {
        "schema_cache_failures_with_progress_gap": len(failed_with_gap),
        "with_reconciled_logical_identity": reconciled_jobs,
        "with_alternate_registered_source": with_alternate_registered_source,
        "with_alternate_record_provenance": with_alternate_record_provenance,
        "with_ambiguous_logical_identity": ambiguous_identity,
        "missing_page_coverage_confirmed": False,
        "alternate_provenance_requires_review": with_alternate_record_provenance > 0,
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
    sources = await fetch_all(db.private_reference_sources)
    records = await fetch_all(db.private_reference_records)
    print(
        json.dumps(
            summarize_schema_cache_alternate_provenance(jobs, sources, records),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache alternate provenance audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
