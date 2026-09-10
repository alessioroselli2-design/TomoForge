#!/usr/bin/env python3
"""Read-only audit for failed import artifacts that resemble a registry source but disagree on identity.

This audit is deliberately conservative. It only compares failed jobs with registry
sources after removing known local artifact suffixes (``_ok`` and long timestamp
suffixes) from filenames. It also inspects ``manual_source_duplicate:<filename>``
errors to detect duplicate claims that point at a different normalized artifact
identity, and checks whether both sides map uniquely to distinct logical sources in
the registry. All findings are diagnostic evidence only; they never authorize an
import retry, registry mutation, OCR, review mutation, or canonicalization.
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
_DUPLICATE_ERROR_PREFIX = "manual_source_duplicate:"


def normalized_artifact_identity(filename: str) -> str:
    """Return a conservative filename identity for diagnostics only."""
    stem = Path(str(filename or "").strip()).stem.casefold()
    previous = None
    while stem and stem != previous:
        previous = stem
        stem = _LONG_NUMERIC_SUFFIX_RE.sub("", stem)
    stem = re.sub(r"(?:[_-]ok)$", "", stem, flags=re.IGNORECASE)
    return _NON_ALNUM_RE.sub("", stem)


def duplicate_error_target(last_error: str) -> str | None:
    """Extract the declared duplicate filename without interpreting it as trusted identity."""
    value = str(last_error or "").strip()
    if not value.casefold().startswith(_DUPLICATE_ERROR_PREFIX):
        return None
    target = value[len(_DUPLICATE_ERROR_PREFIX) :].strip()
    return target or None


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
    duplicate_claims = 0
    cross_identity_duplicate_claims = 0
    registry_distinct_logical_source_claims = 0
    mismatched_job_ids: list[str] = []
    cross_identity_duplicate_job_ids: list[str] = []
    registry_distinct_logical_source_job_ids: list[str] = []

    for job in jobs:
        if str(job.get("status") or "") != "failed":
            continue
        filename = str(job.get("filename") or "").strip()
        if not filename:
            continue
        examined += 1
        identity = normalized_artifact_identity(filename)
        candidates = by_identity.get(identity, []) if identity else []

        duplicate_target = duplicate_error_target(str(job.get("last_error") or ""))
        if duplicate_target:
            duplicate_claims += 1
            target_identity = normalized_artifact_identity(duplicate_target)
            target_candidates = by_identity.get(target_identity, []) if target_identity else []
            if identity and target_identity and identity != target_identity:
                cross_identity_duplicate_claims += 1
                job_id = str(job.get("id") or "").strip()
                if job_id:
                    cross_identity_duplicate_job_ids.append(job_id)

                if len(candidates) == 1 and len(target_candidates) == 1:
                    job_logical_source = str(candidates[0].get("logical_source_id") or "").strip()
                    target_logical_source = str(target_candidates[0].get("logical_source_id") or "").strip()
                    if (
                        job_logical_source
                        and target_logical_source
                        and job_logical_source != target_logical_source
                    ):
                        registry_distinct_logical_source_claims += 1
                        if job_id:
                            registry_distinct_logical_source_job_ids.append(job_id)

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
        "failed_jobs_with_duplicate_claim": duplicate_claims,
        "failed_jobs_with_cross_identity_duplicate_claim": cross_identity_duplicate_claims,
        "failed_jobs_with_registry_distinct_logical_source_duplicate_claim": registry_distinct_logical_source_claims,
        "mismatched_failed_job_ids": sorted(set(mismatched_job_ids)),
        "cross_identity_duplicate_failed_job_ids": sorted(set(cross_identity_duplicate_job_ids)),
        "registry_distinct_logical_source_duplicate_failed_job_ids": sorted(
            set(registry_distinct_logical_source_job_ids)
        ),
        "normalized_filename_evidence_is_diagnostic_only": True,
        "duplicate_target_identity_is_diagnostic_only": True,
        "registry_logical_source_evidence_is_diagnostic_only": True,
        "cross_identity_duplicate_requires_manual_reconciliation": bool(cross_identity_duplicate_claims),
        "registry_distinct_logical_source_duplicate_requires_manual_reconciliation": bool(
            registry_distinct_logical_source_claims
        ),
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
