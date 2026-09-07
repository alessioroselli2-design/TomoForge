#!/usr/bin/env python3
"""Read-only prioritization audit for sources that require vision/OCR.

This audit reports only aggregate metadata. It never generates OCR, downloads
source documents, writes to the database, retries imports, or authorizes
canonicalization.
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

from scripts.audit_manual_import_readiness import fetch_all
from scripts.audit_schema_cache_logical_provenance import _normalized_source_name


def summarize_vision_required_backlog(sources: list[dict], jobs: list[dict]) -> dict[str, Any]:
    vision_sources = [s for s in sources if str(s.get("text_mode") or "") == "vision_required"]
    import_states = Counter(str(s.get("import_state") or "unknown") for s in vision_sources)
    total_pages = sum(int(s.get("physical_pages") or 0) for s in vision_sources)

    by_normalized_name: dict[str, list[dict]] = {}
    for source in vision_sources:
        normalized = _normalized_source_name(source.get("physical_filename"))
        if normalized:
            by_normalized_name.setdefault(normalized, []).append(source)

    matched_failed_jobs = 0
    unmatched_failed_jobs = 0
    schema_cache_failed_jobs = 0
    source_missing_failed_jobs = 0
    duplicate_failed_jobs = 0
    matched_failed_pages_remaining = 0
    matched_failed_jobs_with_explicit_ocr_pages = 0
    matched_failed_jobs_without_explicit_ocr_pages = 0
    matched_schema_cache_failed_jobs = 0

    for job in jobs:
        if str(job.get("status") or "") != "failed":
            continue
        normalized = _normalized_source_name(job.get("filename"))
        matches = by_normalized_name.get(normalized, []) if normalized else []
        is_unique_vision_match = len(matches) == 1
        error = str(job.get("last_error") or "")
        is_schema_cache = "PGRST204" in error or "schema cache" in error.lower()

        if is_unique_vision_match:
            matched_failed_jobs += 1
            page_count = int(job.get("page_count") or 0)
            current_page = int(job.get("current_page") or 0)
            if page_count > current_page:
                matched_failed_pages_remaining += page_count - current_page

            pages_needing_ocr = job.get("pages_needing_ocr") or []
            if pages_needing_ocr:
                matched_failed_jobs_with_explicit_ocr_pages += 1
            else:
                matched_failed_jobs_without_explicit_ocr_pages += 1
            if is_schema_cache:
                matched_schema_cache_failed_jobs += 1
        else:
            unmatched_failed_jobs += 1

        if is_schema_cache:
            schema_cache_failed_jobs += 1
        elif "manual_source_missing" in error:
            source_missing_failed_jobs += 1
        elif "manual_source_duplicate" in error:
            duplicate_failed_jobs += 1

    return {
        "vision_sources_total": len(vision_sources),
        "vision_sources_catalogued": import_states["catalogued"],
        "vision_sources_excluded": import_states["excluded"],
        "vision_pages_total": total_pages,
        "failed_jobs_matched_to_single_vision_source": matched_failed_jobs,
        "failed_jobs_not_uniquely_matched_to_vision_source": unmatched_failed_jobs,
        "failed_jobs_schema_cache": schema_cache_failed_jobs,
        "failed_jobs_source_missing": source_missing_failed_jobs,
        "failed_jobs_source_duplicate": duplicate_failed_jobs,
        "matched_schema_cache_failed_jobs": matched_schema_cache_failed_jobs,
        "matched_failed_jobs_with_explicit_ocr_pages": matched_failed_jobs_with_explicit_ocr_pages,
        "matched_failed_jobs_without_explicit_ocr_pages": matched_failed_jobs_without_explicit_ocr_pages,
        "matched_failed_pages_remaining": matched_failed_pages_remaining,
        "ocr_generation_authorized": False,
        "database_write_authorized": False,
        "automatic_retry_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    sources, jobs = await asyncio.gather(
        fetch_all(db.private_reference_sources),
        fetch_all(db.private_manual_import_jobs),
    )
    print(json.dumps(summarize_vision_required_backlog(sources, jobs), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Vision-required backlog audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
