#!/usr/bin/env python3
"""Read-only parser recoverability audit for schema-cache failures.

Classifies unresolved page gaps conservatively from registered source text modes.
It never runs parsing/OCR, retries imports, writes database state, or authorizes
canonicalization. Mixed/unknown sources remain indeterminate without page-level
evidence.
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

from scripts.audit_manual_import_readiness import _has_record_activity, _is_schema_cache_failure, fetch_all
from scripts.audit_schema_cache_logical_provenance import _normalized_source_name
from scripts.audit_schema_cache_page_provenance import _page_number


def summarize_schema_cache_parser_recoverability(
    jobs: list[dict], sources: list[dict], records: list[dict]
) -> dict[str, Any]:
    targets = [
        job for job in jobs
        if str(job.get("status") or "") == "failed"
        and _is_schema_cache_failure(job)
        and _has_record_activity(job)
        and isinstance(job.get("page_count"), int)
        and int(job["page_count"]) > 0
    ]

    sources_by_name: dict[str, list[dict]] = {}
    for source in sources:
        key = _normalized_source_name(source.get("physical_filename"))
        if key:
            sources_by_name.setdefault(key, []).append(source)

    pages_by_name: dict[str, set[int]] = {}
    for record in records:
        refs = record.get("source_refs")
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            key = _normalized_source_name(ref.get("filename"))
            page = _page_number(ref.get("page"))
            if key and page is not None and page > 0:
                pages_by_name.setdefault(key, set()).add(page)

    parser_only_pages = 0
    ocr_required_pages = 0
    indeterminate_pages = 0
    unresolved_pages_total = 0
    classified_jobs = 0
    ambiguous_jobs = 0

    for job in targets:
        key = _normalized_source_name(job.get("filename"))
        matches = sources_by_name.get(key, [])
        active = [s for s in matches if str(s.get("source_status") or "") == "active"]
        if len(active) != 1:
            ambiguous_jobs += 1
            continue

        classified_jobs += 1
        page_count = int(job["page_count"])
        observed = {p for p in pages_by_name.get(key, set()) if 1 <= p <= page_count}
        missing = set(range(1, page_count + 1)) - observed
        unresolved_pages_total += len(missing)
        mode = str(active[0].get("text_mode") or "unknown")
        declared_ocr = {
            int(p) for p in (job.get("pages_needing_ocr") or [])
            if isinstance(p, int) and 1 <= int(p) <= page_count
        }

        if mode == "text":
            parser_only_pages += len(missing - declared_ocr)
            ocr_required_pages += len(missing & declared_ocr)
        elif mode == "vision_required":
            ocr_required_pages += len(missing)
        else:
            # mixed/document/unknown need page-level evidence before classification.
            ocr_required_pages += len(missing & declared_ocr)
            indeterminate_pages += len(missing - declared_ocr)

    return {
        "schema_cache_failures_with_record_activity": len(targets),
        "jobs_with_unambiguous_active_source": classified_jobs,
        "jobs_with_ambiguous_or_missing_source": ambiguous_jobs,
        "unresolved_pages_total": unresolved_pages_total,
        "parser_only_candidate_pages": parser_only_pages,
        "ocr_required_pages_from_existing_evidence": ocr_required_pages,
        "indeterminate_pages_requiring_page_level_evidence": indeterminate_pages,
        "parser_recovery_executed": False,
        "ocr_executed": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "record_set_completeness_confirmed": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db
    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    jobs = await fetch_all(db.private_manual_import_jobs)
    sources = await fetch_all(db.private_reference_sources)
    records = await fetch_all(db.private_reference_records)
    print(json.dumps(summarize_schema_cache_parser_recoverability(jobs, sources, records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Schema-cache parser recoverability audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
