#!/usr/bin/env python3
"""Read-only continuity audit for page provenance on failed schema-cache imports.

The presence of a reference to the final page is not proof of continuous coverage.
This audit measures missing page references before and after each failed job's
reported progress while keeping every mutation/retry/canonicalization gate closed.
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


def summarize_schema_cache_page_continuity(
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
        and 0 <= int(job["current_page"]) < int(job["page_count"])
    ]

    refs_by_source: dict[str, set[int]] = {}
    for record in records:
        source_refs = record.get("source_refs")
        if not isinstance(source_refs, list):
            continue
        for ref in source_refs:
            if not isinstance(ref, dict):
                continue
            normalized = _normalized_source_name(ref.get("filename"))
            page = _page_number(ref.get("page"))
            if normalized and page is not None and page > 0:
                refs_by_source.setdefault(normalized, set()).add(page)

    nominal_missing_pages = 0
    observed_pages_in_declared_range = 0
    observed_pages_after_progress = 0
    missing_pages_through_progress = 0
    missing_pages_after_progress = 0
    contiguous_through_progress = 0
    fully_covered_after_progress = 0

    for job in failed_with_gap:
        normalized = _normalized_source_name(job.get("filename"))
        current_page = int(job["current_page"])
        page_count = int(job["page_count"])
        pages = {
            page
            for page in refs_by_source.get(normalized, set())
            if 1 <= page <= page_count
        }

        nominal_missing_pages += page_count - current_page
        observed_pages_in_declared_range += len(pages)
        observed_pages_after_progress += sum(page > current_page for page in pages)

        missing_before = sum(page not in pages for page in range(1, current_page + 1))
        missing_after = sum(
            page not in pages for page in range(current_page + 1, page_count + 1)
        )
        missing_pages_through_progress += missing_before
        missing_pages_after_progress += missing_after
        if missing_before == 0:
            contiguous_through_progress += 1
        if missing_after == 0:
            fully_covered_after_progress += 1

    return {
        "schema_cache_failures_with_progress_gap": len(failed_with_gap),
        "nominal_missing_pages": nominal_missing_pages,
        "observed_pages_in_declared_range": observed_pages_in_declared_range,
        "observed_pages_after_progress": observed_pages_after_progress,
        "missing_pages_through_reported_progress": missing_pages_through_progress,
        "missing_pages_after_reported_progress": missing_pages_after_progress,
        "jobs_contiguous_through_reported_progress": contiguous_through_progress,
        "jobs_fully_covered_after_reported_progress": fully_covered_after_progress,
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
            summarize_schema_cache_page_continuity(jobs, records),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache page continuity audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
