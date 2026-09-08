#!/usr/bin/env python3
"""Read-only audit of the record footprint left by failed manual import jobs.

The audit links records only through an exact source_key == failed job filename
match, then reports aggregate review-state counts. It never infers missing
content, retries imports, changes review states, runs OCR, or canonicalizes data.
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


def summarize_failed_import_record_footprint(
    jobs: list[dict], records: list[dict]
) -> dict[str, Any]:
    failed_jobs = [
        job
        for job in jobs
        if str(job.get("status") or "unknown") == "failed"
        and str(job.get("filename") or "").strip()
    ]
    failed_filenames = {
        str(job.get("filename") or "").strip()
        for job in failed_jobs
    }

    matched_records = [
        record
        for record in records
        if str(record.get("source_key") or "").strip() in failed_filenames
    ]
    review = Counter(str(row.get("review_status") or "unknown") for row in matched_records)
    linked_jobs = {
        str(record.get("source_key") or "").strip()
        for record in matched_records
        if str(record.get("source_key") or "").strip()
    }
    unresolved_failed_job_ids = sorted(
        str(job.get("id") or "").strip()
        for job in failed_jobs
        if str(job.get("filename") or "").strip() not in linked_jobs
        and str(job.get("id") or "").strip()
    )

    return {
        "failed_jobs_total": len(failed_jobs),
        "failed_jobs_with_exact_record_footprint": len(linked_jobs),
        "failed_jobs_without_exact_record_footprint": max(
            0,
            len(failed_filenames) - len(linked_jobs),
        ),
        "unresolved_failed_job_ids": unresolved_failed_job_ids,
        "records_exactly_linked_to_failed_jobs": len(matched_records),
        "linked_records_verified": review["verified"],
        "linked_records_needs_review": review["needs_review"],
        "linked_records_pending": review["pending"],
        "linked_records_other_review_states": len(matched_records)
        - review["verified"]
        - review["needs_review"]
        - review["pending"],
        "exact_source_key_evidence_only": True,
        "record_set_completeness_confirmed": False,
        "automatic_retry_authorized": False,
        "review_state_mutation_authorized": False,
        "database_write_authorized": False,
        "ocr_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs, records = await asyncio.gather(
        fetch_all(db.private_manual_import_jobs),
        fetch_all(db.private_reference_records),
    )
    print(json.dumps(summarize_failed_import_record_footprint(jobs, records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Failed import record footprint audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
