#!/usr/bin/env python3
"""Read-only classification of residual ``manual_source_missing`` jobs.

The audit preserves the failed-job and registry provenance side by side. Only
a unique, non-empty SHA-256 match is considered sufficient provenance evidence;
filename and normalized filename-alias matches remain diagnostic. Every result
stays behind manual review and the audit never retries work, mutates Supabase, or
authorizes canonicalization.
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

from scripts.audit_failed_import_source_provenance import _normalized_filename_alias_key
from scripts.audit_manual_import_readiness import fetch_all

AMBIGUOUS_REVIEW = "AMBIGUOUS_REVIEW"
PROVENANCE_MATCH_REVIEW = "PROVENANCE_MATCH_REVIEW"


def _normalized_sha(value: Any) -> str:
    return str(value or "").strip().casefold()


def _source_provenance(source: dict[str, Any]) -> dict[str, Any]:
    """Project only provenance and review-gate metadata from a registry row."""
    return {
        field: source.get(field)
        for field in (
            "id",
            "physical_filename",
            "physical_sha256",
            "physical_pages",
            "logical_source_id",
            "language",
            "source_role",
            "source_status",
        )
    }


def summarize_remaining_manual_source_missing(
    jobs: list[dict[str, Any]], sources: list[dict[str, Any]]
) -> dict[str, Any]:
    """Classify failed missing-source jobs without changing either input."""
    sources_by_sha: dict[str, list[dict[str, Any]]] = {}
    sources_by_filename: dict[str, list[dict[str, Any]]] = {}
    sources_by_alias: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        sha = _normalized_sha(source.get("physical_sha256"))
        filename = str(source.get("physical_filename") or "").strip().casefold()
        alias = _normalized_filename_alias_key(filename)
        if sha:
            sources_by_sha.setdefault(sha, []).append(source)
        if filename:
            sources_by_filename.setdefault(filename, []).append(source)
        if alias:
            sources_by_alias.setdefault(alias, []).append(source)

    cases: list[dict[str, Any]] = []
    for job in jobs:
        if str(job.get("status") or "") != "failed":
            continue
        if str(job.get("last_error") or "").strip() != "manual_source_missing":
            continue

        filename = str(job.get("filename") or "").strip()
        fingerprint = _normalized_sha(job.get("source_fingerprint"))
        exact_sha_matches = sources_by_sha.get(fingerprint, []) if fingerprint else []
        exact_filename_matches = sources_by_filename.get(filename.casefold(), []) if filename else []
        alias = _normalized_filename_alias_key(filename)
        alias_matches = sources_by_alias.get(alias, []) if alias else []
        sufficient = bool(fingerprint) and len(exact_sha_matches) == 1
        classification = PROVENANCE_MATCH_REVIEW if sufficient else AMBIGUOUS_REVIEW

        cases.append(
            {
                "job_id": str(job.get("id") or "").strip(),
                "job_filename": filename,
                "job_source_fingerprint": fingerprint,
                "job_source_language": job.get("source_language"),
                "job_page_count": job.get("page_count"),
                "job_record_activity": {
                    field: int(job.get(field) or 0)
                    for field in (
                        "records_imported",
                        "records_updated",
                        "records_flagged",
                        "records_skipped",
                    )
                },
                "exact_sha_registry_matches": [
                    _source_provenance(source) for source in exact_sha_matches
                ],
                "exact_filename_registry_matches": [
                    _source_provenance(source) for source in exact_filename_matches
                ],
                "filename_alias_registry_matches": [
                    _source_provenance(source) for source in alias_matches
                ],
                "classification": classification,
                "evidence_sufficient_for_provenance_match": sufficient,
                "requires_manual_review": True,
            }
        )

    cases.sort(key=lambda case: (case["job_id"], case["job_filename"]))
    return {
        "manual_source_missing_cases": len(cases),
        "classification_counts": {
            classification: sum(case["classification"] == classification for case in cases)
            for classification in (AMBIGUOUS_REVIEW, PROVENANCE_MATCH_REVIEW)
            if any(case["classification"] == classification for case in cases)
        },
        "cases": cases,
        "filename_evidence_is_diagnostic_only": True,
        "provenance_match_bypasses_review": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
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
    print(json.dumps(summarize_remaining_manual_source_missing(jobs, sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Residual manual-source audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
