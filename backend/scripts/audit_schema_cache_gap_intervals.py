#!/usr/bin/env python3
"""Read-only interval audit for page-provenance gaps on schema-cache failures.

Page counts alone do not distinguish isolated provenance holes from continuous
missing ranges. This audit groups missing pages into contiguous intervals before
and after each failed job's reported progress. It emits aggregate metrics only
and keeps every mutation/retry/OCR/canonicalization gate closed.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Iterable

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


def _contiguous_intervals(pages: Iterable[int]) -> list[tuple[int, int]]:
    ordered = sorted(set(pages))
    if not ordered:
        return []

    intervals: list[tuple[int, int]] = []
    start = previous = ordered[0]
    for page in ordered[1:]:
        if page == previous + 1:
            previous = page
            continue
        intervals.append((start, previous))
        start = previous = page
    intervals.append((start, previous))
    return intervals


def _interval_metrics(intervals: list[tuple[int, int]]) -> dict[str, int]:
    lengths = [end - start + 1 for start, end in intervals]
    isolated = sum(length == 1 for length in lengths)
    contiguous = sum(length > 1 for length in lengths)
    pages_in_contiguous = sum(length for length in lengths if length > 1)
    return {
        "interval_count": len(intervals),
        "isolated_page_count": isolated,
        "contiguous_interval_count": contiguous,
        "pages_in_contiguous_intervals": pages_in_contiguous,
        "longest_interval_pages": max(lengths, default=0),
    }


def summarize_schema_cache_gap_intervals(
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

    totals = {
        "missing_pages": 0,
        "interval_count": 0,
        "isolated_page_count": 0,
        "contiguous_interval_count": 0,
        "pages_in_contiguous_intervals": 0,
        "longest_interval_pages": 0,
    }
    before = {key: 0 for key in totals}
    after = {key: 0 for key in totals}
    jobs_with_contiguous_gaps = 0
    jobs_with_only_isolated_gaps = 0

    for job in failed_with_gap:
        normalized = _normalized_source_name(job.get("filename"))
        current_page = int(job["current_page"])
        page_count = int(job["page_count"])
        observed = {
            page
            for page in refs_by_source.get(normalized, set())
            if 1 <= page <= page_count
        }

        missing_before = [
            page for page in range(1, current_page + 1) if page not in observed
        ]
        missing_after = [
            page
            for page in range(current_page + 1, page_count + 1)
            if page not in observed
        ]
        before_intervals = _contiguous_intervals(missing_before)
        after_intervals = _contiguous_intervals(missing_after)
        combined_intervals = before_intervals + after_intervals

        before_metrics = _interval_metrics(before_intervals)
        after_metrics = _interval_metrics(after_intervals)
        combined_metrics = _interval_metrics(combined_intervals)

        before["missing_pages"] += len(missing_before)
        after["missing_pages"] += len(missing_after)
        totals["missing_pages"] += len(missing_before) + len(missing_after)

        for key in (
            "interval_count",
            "isolated_page_count",
            "contiguous_interval_count",
            "pages_in_contiguous_intervals",
        ):
            before[key] += before_metrics[key]
            after[key] += after_metrics[key]
            totals[key] += combined_metrics[key]
        before["longest_interval_pages"] = max(
            before["longest_interval_pages"], before_metrics["longest_interval_pages"]
        )
        after["longest_interval_pages"] = max(
            after["longest_interval_pages"], after_metrics["longest_interval_pages"]
        )
        totals["longest_interval_pages"] = max(
            totals["longest_interval_pages"], combined_metrics["longest_interval_pages"]
        )

        if combined_metrics["contiguous_interval_count"] > 0:
            jobs_with_contiguous_gaps += 1
        elif combined_metrics["isolated_page_count"] > 0:
            jobs_with_only_isolated_gaps += 1

    return {
        "schema_cache_failures_with_progress_gap": len(failed_with_gap),
        "missing_pages_total": totals["missing_pages"],
        "missing_gap_intervals_total": totals["interval_count"],
        "isolated_missing_pages_total": totals["isolated_page_count"],
        "contiguous_gap_intervals_total": totals["contiguous_interval_count"],
        "pages_in_contiguous_gaps_total": totals["pages_in_contiguous_intervals"],
        "longest_gap_pages": totals["longest_interval_pages"],
        "missing_pages_through_reported_progress": before["missing_pages"],
        "gap_intervals_through_reported_progress": before["interval_count"],
        "longest_gap_through_reported_progress": before["longest_interval_pages"],
        "missing_pages_after_reported_progress": after["missing_pages"],
        "gap_intervals_after_reported_progress": after["interval_count"],
        "longest_gap_after_reported_progress": after["longest_interval_pages"],
        "jobs_with_contiguous_gaps": jobs_with_contiguous_gaps,
        "jobs_with_only_isolated_gaps": jobs_with_only_isolated_gaps,
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
            summarize_schema_cache_gap_intervals(jobs, records),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache gap interval audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
