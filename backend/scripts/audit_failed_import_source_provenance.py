#!/usr/bin/env python3
"""Read-only audit of source provenance for failed manual import jobs.

The audit classifies only exact registry evidence. It never changes source
metadata, retries imports, generates OCR, or authorizes canonicalization.
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


def _source_failure(error: str) -> bool:
    return "manual_source_missing" in error or "manual_source_duplicate" in error


def _duplicate_target(error: str) -> str | None:
    marker = "manual_source_duplicate:"
    if marker not in error:
        return None
    value = error.split(marker, 1)[1].strip()
    return value or None


def summarize_failed_import_source_provenance(
    sources: list[dict], jobs: list[dict]
) -> dict[str, Any]:
    by_sha: dict[str, list[dict]] = {}
    by_filename: dict[str, list[dict]] = {}
    for source in sources:
        sha = str(source.get("physical_sha256") or "").strip().lower()
        filename = str(source.get("physical_filename") or "").strip().casefold()
        if sha:
            by_sha.setdefault(sha, []).append(source)
        if filename:
            by_filename.setdefault(filename, []).append(source)

    outcomes: Counter[str] = Counter()
    duplicate_targets_found = 0
    source_failures = 0

    for job in jobs:
        if str(job.get("status") or "") != "failed":
            continue
        error = str(job.get("last_error") or "")
        if not _source_failure(error):
            continue

        source_failures += 1
        fingerprint = str(job.get("source_fingerprint") or "").strip().lower()
        filename = str(job.get("filename") or "").strip().casefold()
        sha_matches = by_sha.get(fingerprint, []) if fingerprint else []
        filename_matches = by_filename.get(filename, []) if filename else []

        if len(sha_matches) == 1:
            outcomes["exact_sha_match"] += 1
        elif len(sha_matches) > 1:
            outcomes["ambiguous_sha_match"] += 1
        elif fingerprint and filename_matches:
            # A filename match cannot override a conflicting/missing exact hash.
            outcomes["filename_match_without_hash_confirmation"] += 1
        elif not fingerprint and len(filename_matches) == 1:
            outcomes["exact_filename_match_no_fingerprint"] += 1
        elif len(filename_matches) > 1:
            outcomes["ambiguous_filename_match"] += 1
        else:
            outcomes["unresolved_no_exact_registry_evidence"] += 1

        duplicate_target = _duplicate_target(error)
        if duplicate_target and by_filename.get(duplicate_target.casefold()):
            duplicate_targets_found += 1

    return {
        "failed_source_jobs_total": source_failures,
        "exact_sha_matches": outcomes["exact_sha_match"],
        "ambiguous_sha_matches": outcomes["ambiguous_sha_match"],
        "filename_matches_without_hash_confirmation": outcomes[
            "filename_match_without_hash_confirmation"
        ],
        "exact_filename_matches_no_fingerprint": outcomes[
            "exact_filename_match_no_fingerprint"
        ],
        "ambiguous_filename_matches": outcomes["ambiguous_filename_match"],
        "unresolved_no_exact_registry_evidence": outcomes[
            "unresolved_no_exact_registry_evidence"
        ],
        "reported_duplicate_targets_present_in_registry": duplicate_targets_found,
        "database_write_authorized": False,
        "automatic_retry_authorized": False,
        "ocr_generation_authorized": False,
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
    print(
        json.dumps(
            summarize_failed_import_source_provenance(sources, jobs), sort_keys=True
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Failed import source provenance audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
