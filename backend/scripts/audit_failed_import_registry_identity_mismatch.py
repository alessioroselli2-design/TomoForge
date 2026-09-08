#!/usr/bin/env python3
"""Read-only audit for failed import artifacts that resemble a registry source but disagree on identity.

This audit is deliberately conservative. It only compares failed jobs with registry
sources after removing known local artifact suffixes (``_ok`` and long timestamp
suffixes) from filenames. A normalized filename match is diagnostic evidence only;
it never authorizes an import retry, registry mutation, OCR, review mutation, or
canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all

_LONG_NUMERIC_SUFFIX_RE = re.compile(r"(?:[_-](?:ok)[_-]?)?(?:[_-]?\d{10,})$", re.IGNORECASE)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalized_artifact_identity(filename: str) -> str:
    """Return a conservative filename identity for diagnostics only."""
    stem = Path(str(filename or "").strip()).stem.casefold()
    previous = None
    while stem and stem != previous:
        previous = stem
        stem = _LONG_NUMERIC_SUFFIX_RE.sub("", stem)
    stem = re.sub(r"(?:[_-]ok)$", "", stem, flags=re.IGNORECASE)
    return _NON_ALNUM_RE.sub("", stem)


def summarize_failed_import_registry_identity_mismatch(
    jobs: list[dict], sources: list[dict]
) -> dict[str, Any]:
    by_identity: dict[str, list[dict]] = {}
    for source in sources:
        identity = normalized_artifact_identity(str(source.get("physical_filename") or ""))
        if identity:
            by_identity.setdefault(identity, []).append(source)

    examined = 0
    exact_identity_candidates = 0
    fingerprint_mismatches = 0
    page_count_mismatches = 0
    ambiguous_candidates = 0
    mismatched_job_ids: list[str] = []

    for job in jobs:
        if str(job.get("status") or "") != "failed":
            continue
        filename = str(job.get("filename") or "").strip()
        if not filename:
            continue
        examined += 1
        identity = normalized_artifact_identity(filename)
        candidates = by_identity.get(identity, []) if identity else []
        if not candidates:
            continue
        exact_identity_candidates += 1
        if len(candidates) != 1:
            ambiguous_candidates += 1
            continue

        source = candidates[0]
        job_sha = str(job.get("source_fingerprint") or "").strip().casefold()
        source_sha = str(source.get("physical_sha256") or "").strip().casefold()
        sha_mismatch = bool(job_sha and source_sha and job_sha != source_sha)

        job_pages = job.get("page_count")
        source_pages = source.get("physical_pages")
        pages_mismatch = (
            isinstance(job_pages, int)
            and isinstance(source_pages, int)
            and job_pages > 0
            and source_pages > 0
            and job_pages != source_pages
        )

        if sha_mismatch:
            fingerprint_mismatches += 1
        if pages_mismatch:
            page_count_mismatches += 1
        if sha_mismatch or pages_mismatch:
            job_id = str(job.get("id") or "").strip()
            if job_id:
                mismatched_job_ids.append(job_id)

    return {
        "failed_jobs_examined": examined,
        "failed_jobs_with_normalized_registry_identity_candidate": exact_identity_candidates,
        "failed_jobs_with_ambiguous_registry_identity_candidate": ambiguous_candidates,
        "failed_jobs_with_fingerprint_mismatch": fingerprint_mismatches,
        "failed_jobs_with_page_count_mismatch": page_count_mismatches,
        "mismatched_failed_job_ids": sorted(set(mismatched_job_ids)),
        "normalized_filename_evidence_is_diagnostic_only": True,
        "registry_identity_confirmed": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "ocr_authorized": False,
        "review_state_mutation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    jobs, sources = await asyncio.gather(
        fetch_all(db.private_manual_import_jobs),
        fetch_all(db.private_reference_sources),
    )
    print(
        json.dumps(
            summarize_failed_import_registry_identity_mismatch(jobs, sources),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Failed import registry identity mismatch audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
