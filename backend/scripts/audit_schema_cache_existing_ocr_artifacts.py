#!/usr/bin/env python3
"""Read-only audit of existing OCR artifacts for schema-cache page gaps.

This audit only inventories files that already exist in the repository checkout. It
never invokes OCR, parses new pages, retries imports, writes Supabase, confirms
record-set completeness, or authorizes canonicalization.

Rendered PNG/JPEG previews are intentionally *not* treated as reusable OCR output.
Only page-scoped ``.ocr.txt`` / ``.ocr.json`` artifacts count as explicit reusable
OCR evidence.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import _has_record_activity, _is_schema_cache_failure, fetch_all
from scripts.audit_schema_cache_logical_provenance import _normalized_source_name
from scripts.audit_schema_cache_page_provenance import _page_number

_PAGE_ARTIFACT_RE = re.compile(r"(?:page[-_.]?)(\d{1,5})(?:\.ocr)?\.(png|jpe?g|txt|json)$", re.IGNORECASE)


def _artifact_page(path: Path) -> int | None:
    match = _PAGE_ARTIFACT_RE.search(path.name)
    if not match:
        return None
    page = int(match.group(1))
    return page if page > 0 else None


def _is_explicit_reusable_ocr(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".ocr.txt") or name.endswith(".ocr.json")


def _artifact_source_key(path: Path) -> str:
    name = path.name
    marker = re.search(r"(?:\.page-|\.page_|-page-|_page-)(\d{1,5})", name, re.IGNORECASE)
    if marker:
        name = name[: marker.start()]
    return _normalized_source_name(name)


def summarize_existing_ocr_artifacts(
    jobs: list[dict], records: list[dict], artifact_paths: list[Path]
) -> dict[str, Any]:
    targets = [
        job for job in jobs
        if str(job.get("status") or "") == "failed"
        and _is_schema_cache_failure(job)
        and _has_record_activity(job)
        and isinstance(job.get("page_count"), int)
        and int(job["page_count"]) > 0
    ]

    observed_by_source: dict[str, set[int]] = {}
    for record in records:
        refs = record.get("source_refs")
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            key = _normalized_source_name(ref.get("filename"))
            page = _page_number(ref.get("page"))
            if key and page is not None and page > 0:
                observed_by_source.setdefault(key, set()).add(page)

    previews_by_source: dict[str, set[int]] = {}
    reusable_by_source: dict[str, set[int]] = {}
    for path in artifact_paths:
        page = _artifact_page(path)
        key = _artifact_source_key(path)
        if page is None or not key:
            continue
        if _is_explicit_reusable_ocr(path):
            reusable_by_source.setdefault(key, set()).add(page)
        elif path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            previews_by_source.setdefault(key, set()).add(page)

    unresolved_total = 0
    preview_only_gap_pages = 0
    reusable_ocr_gap_pages = 0
    per_job: list[dict[str, Any]] = []

    for job in targets:
        key = _normalized_source_name(job.get("filename"))
        page_count = int(job["page_count"])
        observed = {p for p in observed_by_source.get(key, set()) if 1 <= p <= page_count}
        missing = set(range(1, page_count + 1)) - observed
        preview_pages = previews_by_source.get(key, set()) & missing
        reusable_pages = reusable_by_source.get(key, set()) & missing
        unresolved_total += len(missing)
        preview_only_gap_pages += len(preview_pages - reusable_pages)
        reusable_ocr_gap_pages += len(reusable_pages)
        per_job.append({
            "filename": job.get("filename"),
            "unresolved_pages": len(missing),
            "preview_only_gap_pages": len(preview_pages - reusable_pages),
            "explicit_reusable_ocr_gap_pages": len(reusable_pages),
        })

    return {
        "schema_cache_failures_with_record_activity": len(targets),
        "unresolved_pages_total": unresolved_total,
        "preview_only_gap_pages": preview_only_gap_pages,
        "explicit_reusable_ocr_gap_pages": reusable_ocr_gap_pages,
        "jobs": per_job,
        "preview_images_count_as_ocr_evidence": False,
        "ocr_executed": False,
        "parser_recovery_executed": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "record_set_completeness_confirmed": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db
    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    jobs = await fetch_all(db.private_manual_import_jobs)
    records = await fetch_all(db.private_reference_records)
    artifact_root = REPO_ROOT / ".agents" / "outputs"
    artifact_paths = [p for p in artifact_root.rglob("*") if p.is_file()] if artifact_root.exists() else []
    result = summarize_existing_ocr_artifacts(jobs, records, artifact_paths)
    print(json.dumps(result, sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Existing OCR artifact audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
