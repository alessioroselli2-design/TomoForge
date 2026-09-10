#!/usr/bin/env python3
"""Read-only context audit for failed import filename-alias candidates.

This diagnostic deliberately stops short of identity reconciliation. It combines
only already-recorded job metadata with registry metadata to expose whether a
single conservative filename-alias candidate agrees on language and page count,
and whether the failed job already shows prior record activity. A mismatched or
unconfirmed content hash always keeps the candidate review-only.
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


def _positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def _job_has_prior_record_activity(job: dict) -> bool:
    return any(
        isinstance(job.get(field), int) and int(job.get(field) or 0) > 0
        for field in ("records_imported", "records_updated", "records_flagged", "records_skipped")
    )


def summarize_failed_import_alias_context(jobs: list[dict], sources: list[dict]) -> dict[str, Any]:
    by_alias: dict[str, list[dict]] = {}
    for source in sources:
        key = _normalized_filename_alias_key(str(source.get("physical_filename") or ""))
        if key:
            by_alias.setdefault(key, []).append(source)

    candidates: list[dict[str, Any]] = []
    for job in jobs:
        if str(job.get("status") or "") != "failed":
            continue
        if "manual_source_missing" not in str(job.get("last_error") or ""):
            continue

        key = _normalized_filename_alias_key(str(job.get("filename") or ""))
        matches = by_alias.get(key, []) if key else []
        if len(matches) != 1:
            continue

        source = matches[0]
        job_sha = str(job.get("source_fingerprint") or "").strip().casefold()
        source_sha = str(source.get("physical_sha256") or "").strip().casefold()
        hash_confirmed = bool(job_sha and source_sha and job_sha == source_sha)
        if hash_confirmed:
            continue

        job_language = str(job.get("source_language") or "").strip().casefold()
        source_language = str(source.get("language") or "").strip().casefold()
        language_comparable = bool(job_language and source_language)
        language_match = language_comparable and job_language == source_language

        job_pages = _positive_int(job.get("page_count"))
        source_pages = _positive_int(source.get("physical_pages"))
        page_count_comparable = job_pages is not None and source_pages is not None
        page_count_match = page_count_comparable and job_pages == source_pages

        candidates.append(
            {
                "job_id": str(job.get("id") or "").strip(),
                "job_filename": str(job.get("filename") or "").strip(),
                "registry_source_id": str(source.get("id") or "").strip(),
                "registry_filename": str(source.get("physical_filename") or "").strip(),
                "logical_source_id": str(source.get("logical_source_id") or "").strip(),
                "job_language": job_language,
                "registry_language": source_language,
                "language_match": language_match,
                "page_count_match": page_count_match,
                "prior_record_activity": _job_has_prior_record_activity(job),
                "hash_confirmed": False,
                "requires_manual_reconciliation": True,
            }
        )

    return {
        "review_only_alias_candidates": len(candidates),
        "alias_candidates_with_language_match": sum(bool(c["language_match"]) for c in candidates),
        "alias_candidates_with_page_count_match": sum(bool(c["page_count_match"]) for c in candidates),
        "alias_candidates_with_prior_record_activity": sum(
            bool(c["prior_record_activity"]) for c in candidates
        ),
        "alias_candidate_logical_source_ids": sorted(
            {str(c["logical_source_id"]) for c in candidates if c["logical_source_id"]}
        ),
        "candidates": sorted(candidates, key=lambda c: (c["job_id"], c["job_filename"])),
        "alias_context_is_diagnostic_only": True,
        "registry_identity_confirmed": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "ocr_authorized": False,
        "translation_authorized": False,
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
    print(json.dumps(summarize_failed_import_alias_context(jobs, sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Failed import alias context audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
