#!/usr/bin/env python3
"""Read-only reciprocal provenance audit for failed import alias candidates.

For failed ``manual_source_missing`` jobs with one normalized filename alias in the
source registry and a non-matching source fingerprint, inspect historical records
linked by exact ``source_key``. For every companion filename found in mixed
``source_refs``, report whether records owned by that companion point back to the
failed-job filename.

Reciprocity is diagnostic evidence only. It does not confirm identity and never
authorizes retry, writes, OCR, translation, review mutation, or canonicalization.
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

from scripts.audit_failed_import_source_provenance import _normalized_filename_alias_key
from scripts.audit_manual_import_readiness import fetch_all


def _ref_filenames(source_refs: Any) -> set[str]:
    if not isinstance(source_refs, list):
        return set()
    return {
        str(ref.get("filename") or "").strip()
        for ref in source_refs
        if isinstance(ref, dict) and str(ref.get("filename") or "").strip()
    }


def summarize_reciprocal_provenance(jobs: list[dict], sources: list[dict], records: list[dict]) -> dict[str, Any]:
    by_alias: dict[str, list[dict]] = {}
    for source in sources:
        key = _normalized_filename_alias_key(str(source.get("physical_filename") or ""))
        if key:
            by_alias.setdefault(key, []).append(source)

    candidates: list[dict[str, Any]] = []
    for job in jobs:
        if str(job.get("status") or "") != "failed" or "manual_source_missing" not in str(job.get("last_error") or ""):
            continue
        filename = str(job.get("filename") or "").strip()
        key = _normalized_filename_alias_key(filename)
        matches = by_alias.get(key, []) if key else []
        if not filename or len(matches) != 1:
            continue
        source = matches[0]
        job_sha = str(job.get("source_fingerprint") or "").strip().casefold()
        source_sha = str(source.get("physical_sha256") or "").strip().casefold()
        if job_sha and source_sha and job_sha == source_sha:
            continue

        companion_counts: Counter[str] = Counter()
        for record in records:
            if str(record.get("source_key") or "").strip() != filename:
                continue
            refs = _ref_filenames(record.get("source_refs"))
            for companion in refs - {filename}:
                companion_counts[companion] += 1

        companions = []
        for companion, forward_count in sorted(companion_counts.items(), key=lambda item: (-item[1], item[0])):
            companion_records = [r for r in records if str(r.get("source_key") or "").strip() == companion]
            reverse_count = sum(filename in _ref_filenames(r.get("source_refs")) for r in companion_records)
            companions.append({
                "filename": companion,
                "forward_mixed_records": forward_count,
                "companion_source_records": len(companion_records),
                "reciprocal_records": reverse_count,
                "has_reciprocal_provenance": reverse_count > 0,
            })

        candidates.append({
            "job_id": str(job.get("id") or "").strip(),
            "job_filename": filename,
            "logical_source_id": str(source.get("logical_source_id") or "").strip(),
            "companions": companions,
            "all_companions_reciprocal": bool(companions) and all(c["has_reciprocal_provenance"] for c in companions),
            "hash_confirmed": False,
            "requires_manual_reconciliation": True,
        })

    return {
        "review_only_alias_candidates": len(candidates),
        "candidates": sorted(candidates, key=lambda c: (c["job_id"], c["job_filename"])),
        "reciprocity_confirms_identity": False,
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
    jobs, sources, records = await asyncio.gather(
        fetch_all(db.private_manual_import_jobs),
        fetch_all(db.private_reference_sources),
        fetch_all(db.private_reference_records),
    )
    print(json.dumps(summarize_reciprocal_provenance(jobs, sources, records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Reciprocal provenance audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
