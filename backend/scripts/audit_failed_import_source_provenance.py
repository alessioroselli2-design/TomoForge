#!/usr/bin/env python3
"""Read-only audit of source provenance for failed manual import jobs.

The audit classifies only exact registry evidence and exact historical artifact
filenames already committed in the repository. Historical artifacts are
strictly diagnostic: they never authorize a registry match, retry, OCR,
database write, or canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
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


def _historical_filenames_from_sample_report(path: Path) -> set[str]:
    """Load exact PDF filenames from the checked-in manual sample report."""
    if not path.is_file():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("manual sample report must contain a JSON list")
    return {
        str(item.get("filename") or "").strip().casefold()
        for item in payload
        if isinstance(item, dict) and str(item.get("filename") or "").strip()
    }


def summarize_failed_import_source_provenance(
    sources: list[dict],
    jobs: list[dict],
    historical_filenames: set[str] | None = None,
) -> dict[str, Any]:
    historical_filenames = {
        str(value).strip().casefold()
        for value in (historical_filenames or set())
        if str(value).strip()
    }
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
    historical_job_filenames_found = 0
    historical_duplicate_targets_found = 0
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

        if filename and filename in historical_filenames:
            historical_job_filenames_found += 1

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
        if duplicate_target:
            normalized_target = duplicate_target.casefold()
            if by_filename.get(normalized_target):
                duplicate_targets_found += 1
            if normalized_target in historical_filenames:
                historical_duplicate_targets_found += 1

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
        "failed_job_filenames_present_in_historical_artifacts": historical_job_filenames_found,
        "reported_duplicate_targets_present_in_historical_artifacts": historical_duplicate_targets_found,
        "historical_artifact_evidence_is_diagnostic_only": True,
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
    historical_filenames = _historical_filenames_from_sample_report(
        REPO_DIR / ".agents" / "outputs" / "manual-sample-report.json"
    )
    print(
        json.dumps(
            summarize_failed_import_source_provenance(
                sources, jobs, historical_filenames=historical_filenames
            ),
            sort_keys=True,
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
