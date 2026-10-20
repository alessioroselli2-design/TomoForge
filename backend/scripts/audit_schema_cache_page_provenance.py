#!/usr/bin/env python3
"""Read-only page-provenance audit for failed schema-cache imports.

This audit measures whether records associated with a failed schema-cache job carry
page-level provenance in ``source_refs`` and whether that provenance reaches the
job's reported progress or declared final page. It is intentionally conservative:
page observations are evidence only and never authorize retry, database writes,
OCR, or canonicalization.
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


def _page_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def summarize_schema_cache_page_provenance(
    jobs: list[dict], records: list[dict]
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

    refs_by_source: dict[str, set[int]] = {}
    records_by_source: dict[str, set[str]] = {}
    for record in records:
        record_id = str(record.get("id") or "")
        source_refs = record.get("source_refs")
        if not isinstance(source_refs, list):
            continue
        for ref in source_refs:
            if not isinstance(ref, dict):
                continue
            normalized = _normalized_source_name(ref.get("filename"))
            page = _page_number(ref.get("page"))
            if not normalized:
                continue
            if record_id:
                records_by_source.setdefault(normalized, set()).add(record_id)
            if page is not None:
                refs_by_source.setdefault(normalized, set()).add(page)

    with_page_provenance = 0
    refs_reach_reported_progress = 0
    refs_reach_declared_end = 0
    total_records_with_matching_refs = 0
    total_distinct_pages_observed = 0
    nominal_missing_pages = 0

    for job in failed_with_gap:
        normalized = _normalized_source_name(job.get("filename"))
        pages = refs_by_source.get(normalized, set())
        matching_records = records_by_source.get(normalized, set())
        current_page = int(job["current_page"])
        page_count = int(job["page_count"])
        nominal_missing_pages += max(page_count - current_page, 0)
        total_records_with_matching_refs += len(matching_records)
        total_distinct_pages_observed += len(pages)
        if pages:
            with_page_provenance += 1
            max_page = max(pages)
            if max_page >= current_page:
                refs_reach_reported_progress += 1
            if max_page >= page_count:
                refs_reach_declared_end += 1

    return {
        "schema_cache_failures_with_progress_gap": len(failed_with_gap),
        "nominal_missing_pages": nominal_missing_pages,
        "jobs_with_page_provenance": with_page_provenance,
        "records_with_matching_source_refs": total_records_with_matching_refs,
        "distinct_pages_observed": total_distinct_pages_observed,
        "jobs_refs_reach_reported_progress": refs_reach_reported_progress,
        "jobs_refs_reach_declared_end": refs_reach_declared_end,
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
    records = await fetch_all(db.private_reference_records)
    print(
        json.dumps(
            summarize_schema_cache_page_provenance(jobs, records),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache page provenance audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
