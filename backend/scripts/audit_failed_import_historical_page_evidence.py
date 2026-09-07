#!/usr/bin/env python3
"""Read-only corroboration of failed-import provenance from checked-in artifacts.

Exact historical filename + page-count agreement is diagnostic evidence only. It
never authorizes source-registry writes, retries, OCR, or canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all

REPORT_PATHS = (
    REPO_DIR / ".agents" / "outputs" / "manual-sample-report.json",
    REPO_DIR / ".agents" / "outputs" / "spell-pdf-analysis.json",
)


def _source_failure(error: str) -> bool:
    return "manual_source_missing" in error or "manual_source_duplicate" in error


def _load_historical_page_counts(paths: list[Path] | tuple[Path, ...]) -> dict[str, set[int]]:
    evidence: dict[str, set[int]] = {}
    for path in paths:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"historical report must contain a JSON list: {path}")
        for item in payload:
            if not isinstance(item, dict):
                continue
            filename = str(item.get("filename") or "").strip().casefold()
            if not filename:
                continue
            try:
                pages = int(item.get("pages"))
            except (TypeError, ValueError):
                continue
            if pages <= 0:
                continue
            evidence.setdefault(filename, set()).add(pages)
    return evidence


def summarize_failed_import_historical_page_evidence(
    jobs: list[dict], historical_page_counts: dict[str, set[int]]
) -> dict[str, Any]:
    failed_source_jobs = 0
    exact_filename_and_page_count = 0
    filename_only_page_mismatch = 0
    no_historical_filename = 0
    matched_jobs: list[dict[str, Any]] = []

    normalized = {
        str(filename).strip().casefold(): {int(p) for p in pages if int(p) > 0}
        for filename, pages in historical_page_counts.items()
        if str(filename).strip()
    }

    for job in jobs:
        if str(job.get("status") or "") != "failed":
            continue
        error = str(job.get("last_error") or "")
        if not _source_failure(error):
            continue
        failed_source_jobs += 1

        filename = str(job.get("filename") or "").strip().casefold()
        try:
            page_count = int(job.get("page_count"))
        except (TypeError, ValueError):
            page_count = 0
        historical_pages = normalized.get(filename)

        if not historical_pages:
            no_historical_filename += 1
            continue
        if page_count > 0 and page_count in historical_pages:
            exact_filename_and_page_count += 1
            matched_jobs.append(
                {
                    "job_id": job.get("id"),
                    "filename": job.get("filename"),
                    "page_count": page_count,
                    "source_fingerprint": job.get("source_fingerprint"),
                }
            )
        else:
            filename_only_page_mismatch += 1

    return {
        "failed_source_jobs_total": failed_source_jobs,
        "exact_historical_filename_and_page_count_matches": exact_filename_and_page_count,
        "historical_filename_page_mismatches": filename_only_page_mismatch,
        "failed_jobs_without_historical_filename": no_historical_filename,
        "matched_jobs": matched_jobs,
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
    evidence = _load_historical_page_counts(REPORT_PATHS)
    print(
        json.dumps(
            summarize_failed_import_historical_page_evidence(jobs, evidence),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Historical page evidence audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
