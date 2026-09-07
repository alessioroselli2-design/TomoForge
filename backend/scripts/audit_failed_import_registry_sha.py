#!/usr/bin/env python3
"""Read-only audit of failed import provenance against the source registry.

Exact physical filename and/or SHA-256 matches are diagnostic only. This script
never authorizes registry writes, retries, OCR, or canonicalization.
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

from scripts.audit_manual_import_readiness import fetch_all


def _source_failure(error: str) -> bool:
    return "manual_source_missing" in error or "manual_source_duplicate" in error


def summarize_failed_import_registry_sha(
    jobs: list[dict], sources: list[dict]
) -> dict[str, Any]:
    by_filename: dict[str, list[dict]] = {}
    by_sha: dict[str, list[dict]] = {}
    for source in sources:
        filename = str(source.get("physical_filename") or "").strip().casefold()
        sha = str(source.get("physical_sha256") or "").strip().casefold()
        if filename:
            by_filename.setdefault(filename, []).append(source)
        if sha:
            by_sha.setdefault(sha, []).append(source)

    counts = {
        "failed_source_jobs_total": 0,
        "exact_filename_and_sha": 0,
        "sha_only": 0,
        "filename_only": 0,
        "no_registry_match": 0,
        "ambiguous_registry_match": 0,
    }
    jobs_out: list[dict[str, Any]] = []

    for job in jobs:
        if str(job.get("status") or "") != "failed":
            continue
        error = str(job.get("last_error") or "")
        if not _source_failure(error):
            continue
        counts["failed_source_jobs_total"] += 1

        filename = str(job.get("filename") or "").strip().casefold()
        sha = str(job.get("source_fingerprint") or "").strip().casefold()
        filename_matches = by_filename.get(filename, []) if filename else []
        sha_matches = by_sha.get(sha, []) if sha else []
        union_ids = {
            str(source.get("id"))
            for source in filename_matches + sha_matches
            if source.get("id") is not None
        }

        if len(union_ids) > 1:
            classification = "ambiguous_registry_match"
        elif filename_matches and sha_matches and union_ids:
            classification = "exact_filename_and_sha"
        elif sha_matches:
            classification = "sha_only"
        elif filename_matches:
            classification = "filename_only"
        else:
            classification = "no_registry_match"
        counts[classification] += 1

        jobs_out.append(
            {
                "job_id": job.get("id"),
                "filename": job.get("filename"),
                "source_fingerprint": job.get("source_fingerprint"),
                "classification": classification,
                "registry_source_ids": sorted(union_ids),
            }
        )

    return {
        **counts,
        "jobs": jobs_out,
        "evidence_is_diagnostic_only": True,
        "registry_write_authorized": False,
        "automatic_retry_authorized": False,
        "ocr_generation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    jobs = await fetch_all(db.private_manual_import_jobs)
    sources = await fetch_all(db.private_reference_sources)
    print(json.dumps(summarize_failed_import_registry_sha(jobs, sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Registry SHA audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
