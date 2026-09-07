#!/usr/bin/env python3
"""Read-only audit of external OCR evidence for schema-cache failures.

The import-job flags ``external_processing_confirmed`` and ``pages_needing_ocr`` are
workflow/control-plane metadata. They are not proof that page-scoped OCR output
exists in R2 or any other external store. This audit inventories explicit artifact
locators already persisted in job metadata while keeping every trust gate closed.

It never calls OCR, downloads objects, retries imports, writes Supabase, confirms
record-set completeness, or authorizes canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Iterable

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import _has_record_activity, _is_schema_cache_failure, fetch_all

_ARTIFACT_LOCATOR_KEYS = {
    "artifact_key",
    "artifact_url",
    "ocr_key",
    "ocr_url",
    "output_key",
    "output_url",
    "r2_key",
    "storage_key",
    "text_key",
    "text_url",
}


def _iter_locator_values(value: Any) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in _ARTIFACT_LOCATOR_KEYS and isinstance(child, str) and child.strip():
                yield normalized_key, child.strip()
            yield from _iter_locator_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_locator_values(child)


def summarize_external_ocr_evidence(jobs: list[dict]) -> dict[str, Any]:
    targets = [
        job
        for job in jobs
        if str(job.get("status") or "") == "failed"
        and _is_schema_cache_failure(job)
        and _has_record_activity(job)
    ]

    locator_candidates = 0
    per_job: list[dict[str, Any]] = []
    for job in targets:
        locators = sorted(set(_iter_locator_values(job.get("pages_needing_ocr"))))
        locator_candidates += len(locators)
        pages_value = job.get("pages_needing_ocr")
        backlog_entries = len(pages_value) if isinstance(pages_value, list) else 0
        per_job.append(
            {
                "filename": job.get("filename"),
                "external_processing_confirmed": bool(job.get("external_processing_confirmed")),
                "pages_needing_ocr_entries": backlog_entries,
                "explicit_external_artifact_locator_candidates": len(locators),
                "external_processing_confirmation_counts_as_artifact_evidence": False,
                "ocr_backlog_marker_counts_as_artifact_evidence": False,
            }
        )

    return {
        "schema_cache_failures_with_record_activity": len(targets),
        "jobs_with_external_processing_confirmed": sum(
            1 for job in targets if bool(job.get("external_processing_confirmed"))
        ),
        "explicit_external_artifact_locator_candidates": locator_candidates,
        "validated_external_ocr_artifacts": 0,
        "external_object_store_checked": False,
        "ocr_executed": False,
        "parser_recovery_executed": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "record_set_completeness_confirmed": False,
        "canonicalization_authorized": False,
        "jobs": per_job,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    jobs = await fetch_all(db.private_manual_import_jobs)
    result = summarize_external_ocr_evidence(jobs)
    print(json.dumps(result, sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"External OCR evidence audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
