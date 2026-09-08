#!/usr/bin/env python3
"""Read-only audit for active catalogued sources that require vision/OCR but have no imported records.

The result is a review gate only. Historical import-job matches are diagnostic
provenance evidence: they never authorize OCR, external processing, import
retries, database writes, review-state changes, or canonicalization.
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


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def summarize_catalogued_vision_zero_import(
    sources: list[dict], jobs: list[dict] | None = None
) -> dict[str, Any]:
    jobs = jobs or []
    jobs_by_sha: dict[str, list[dict]] = {}
    jobs_by_filename: dict[str, list[dict]] = {}
    for job in jobs:
        sha = _norm(job.get("source_fingerprint"))
        filename = _norm(job.get("filename"))
        if sha:
            jobs_by_sha.setdefault(sha, []).append(job)
        if filename:
            jobs_by_filename.setdefault(filename, []).append(job)

    blocked_ids: list[str] = []
    exact_job_evidence_ids: list[str] = []
    filename_only_job_evidence_ids: list[str] = []
    no_exact_job_evidence_ids: list[str] = []
    ambiguous_job_evidence_ids: list[str] = []
    examined = 0

    for source in sources:
        if str(source.get("source_status") or "") != "active":
            continue
        if str(source.get("import_state") or "") != "catalogued":
            continue
        if str(source.get("text_mode") or "") not in {"vision_required", "mixed"}:
            continue
        examined += 1
        imported = source.get("imported_record_count")
        if imported not in (None, 0):
            continue

        source_id = str(source.get("id") or "").strip()
        if not source_id:
            continue
        blocked_ids.append(source_id)

        sha = _norm(source.get("physical_sha256"))
        filename = _norm(source.get("physical_filename"))
        sha_matches = jobs_by_sha.get(sha, []) if sha else []
        filename_matches = jobs_by_filename.get(filename, []) if filename else []

        sha_job_ids = {_norm(job.get("id")) for job in sha_matches if _norm(job.get("id"))}
        filename_job_ids = {
            _norm(job.get("id")) for job in filename_matches if _norm(job.get("id"))
        }
        candidate_job_ids = sha_job_ids | filename_job_ids

        if len(candidate_job_ids) > 1:
            ambiguous_job_evidence_ids.append(source_id)
        elif len(sha_matches) == 1:
            exact_job_evidence_ids.append(source_id)
        elif filename_matches:
            # Filename-only evidence is useful for review but cannot establish
            # provenance when an exact physical hash is unavailable/mismatched.
            filename_only_job_evidence_ids.append(source_id)
        else:
            no_exact_job_evidence_ids.append(source_id)

    return {
        "active_catalogued_vision_sources_examined": examined,
        "active_catalogued_vision_sources_with_zero_imported_records": len(blocked_ids),
        "blocked_source_ids": sorted(blocked_ids),
        "zero_import_sources_with_exact_import_job_evidence": len(exact_job_evidence_ids),
        "zero_import_sources_with_filename_only_job_evidence": len(
            filename_only_job_evidence_ids
        ),
        "zero_import_sources_with_ambiguous_job_evidence": len(
            ambiguous_job_evidence_ids
        ),
        "zero_import_sources_without_exact_import_job_evidence": len(
            no_exact_job_evidence_ids
        ),
        "source_ids_with_exact_import_job_evidence": sorted(exact_job_evidence_ids),
        "source_ids_with_filename_only_job_evidence": sorted(
            filename_only_job_evidence_ids
        ),
        "source_ids_with_ambiguous_job_evidence": sorted(ambiguous_job_evidence_ids),
        "source_ids_without_exact_import_job_evidence": sorted(
            no_exact_job_evidence_ids
        ),
        "requires_authorized_text_extraction_before_import": bool(blocked_ids),
        "historical_import_job_evidence_is_diagnostic_only": True,
        "evidence_is_diagnostic_only": True,
        "ocr_authorized": False,
        "external_processing_authorized": False,
        "automatic_import_authorized": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "review_state_mutation_authorized": False,
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
            summarize_catalogued_vision_zero_import(sources, jobs), sort_keys=True
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Vision zero-import audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
