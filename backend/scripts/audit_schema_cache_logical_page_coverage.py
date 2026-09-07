#!/usr/bin/env python3
"""Read-only logical-identity page coverage audit for schema-cache failures.

For failed schema-cache imports with partial progress, this audit compares page
provenance from the job's own physical source with page provenance from every
registered physical source sharing the same reconciled logical source identity.
It only measures whether alternate provenance closes gaps; it never treats that
as proof of record-set completeness and never authorizes retry, writes, OCR, or
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
from scripts.audit_schema_cache_page_provenance import _page_number


def summarize_schema_cache_logical_page_coverage(
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
        and 0 <= int(job["current_page"]) < int(job["page_count"])
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

    pages_by_normalized_filename: dict[str, set[int]] = {}
    for record in records:
        refs = record.get("source_refs")
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            normalized = _normalized_source_name(ref.get("filename"))
            page = _page_number(ref.get("page"))
            if normalized and page is not None and page > 0:
                pages_by_normalized_filename.setdefault(normalized, set()).add(page)

    reconciled_jobs = 0
    ambiguous_jobs = 0
    direct_missing_pages = 0
    logical_missing_pages = 0
    gaps_closed_by_alternate_provenance = 0
    jobs_with_any_gap_closed = 0
    jobs_with_all_direct_gaps_closed = 0

    for job in failed_with_gap:
        filename = str(job.get("filename") or "").strip()
        normalized_job = _normalized_source_name(filename)
        registry_matches = sources_by_normalized_name.get(normalized_job, [])
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
            ambiguous_jobs += 1
            continue

        reconciled_jobs += 1
        logical_id = next(iter(logical_ids))
        logical_source_names = {
            _normalized_source_name(source.get("physical_filename"))
            for source in sources_by_logical_id.get(logical_id, [])
            if _normalized_source_name(source.get("physical_filename"))
        }

        page_count = int(job["page_count"])
        direct_pages = {
            page
            for page in pages_by_normalized_filename.get(normalized_job, set())
            if 1 <= page <= page_count
        }
        logical_pages: set[int] = set()
        for normalized_name in logical_source_names:
            logical_pages.update(
                page
                for page in pages_by_normalized_filename.get(normalized_name, set())
                if 1 <= page <= page_count
            )

        direct_missing = set(range(1, page_count + 1)) - direct_pages
        logical_missing = set(range(1, page_count + 1)) - logical_pages
        closed = direct_missing - logical_missing

        direct_missing_pages += len(direct_missing)
        logical_missing_pages += len(logical_missing)
        gaps_closed_by_alternate_provenance += len(closed)
        if closed:
            jobs_with_any_gap_closed += 1
        if direct_missing and not logical_missing:
            jobs_with_all_direct_gaps_closed += 1

    return {
        "schema_cache_failures_with_progress_gap": len(failed_with_gap),
        "with_reconciled_logical_identity": reconciled_jobs,
        "with_ambiguous_logical_identity": ambiguous_jobs,
        "direct_missing_pages_total": direct_missing_pages,
        "logical_identity_missing_pages_total": logical_missing_pages,
        "direct_gaps_closed_by_alternate_provenance": gaps_closed_by_alternate_provenance,
        "jobs_with_any_gap_closed_by_alternate_provenance": jobs_with_any_gap_closed,
        "jobs_with_all_direct_gaps_closed_by_alternate_provenance": jobs_with_all_direct_gaps_closed,
        "record_set_completeness_confirmed": False,
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
            summarize_schema_cache_logical_page_coverage(jobs, sources, records),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache logical page coverage audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
