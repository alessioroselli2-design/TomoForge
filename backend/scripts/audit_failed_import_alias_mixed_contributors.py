#!/usr/bin/env python3
"""Read-only audit of companion files in mixed provenance alias records.

This audit is intentionally conservative. It only considers failed
``manual_source_missing`` jobs that have exactly one normalized filename alias
candidate in the source registry and whose job fingerprint does not match the
registry source hash. Historical records are linked only by exact
``source_key == job filename``. For records whose ``source_refs`` mention both
the job filename and other files, it counts which companion filenames occur.

The output is diagnostic only. It never confirms source identity and never
authorizes retry, writes, OCR, translation, review mutation, or
canonicalization.
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


def summarize_failed_alias_mixed_contributors(
    jobs: list[dict], sources: list[dict], records: list[dict]
) -> dict[str, Any]:
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

        filename = str(job.get("filename") or "").strip()
        alias_key = _normalized_filename_alias_key(filename)
        matches = by_alias.get(alias_key, []) if alias_key else []
        if not filename or len(matches) != 1:
            continue

        source = matches[0]
        job_sha = str(job.get("source_fingerprint") or "").strip().casefold()
        source_sha = str(source.get("physical_sha256") or "").strip().casefold()
        if job_sha and source_sha and job_sha == source_sha:
            continue

        companion_counts: Counter[str] = Counter()
        mixed_records = 0
        linked_records = 0
        for record in records:
            if str(record.get("source_key") or "").strip() != filename:
                continue
            linked_records += 1
            ref_names = _ref_filenames(record.get("source_refs"))
            if filename not in ref_names or len(ref_names) <= 1:
                continue
            mixed_records += 1
            for companion in ref_names - {filename}:
                companion_counts[companion] += 1

        candidates.append(
            {
                "job_id": str(job.get("id") or "").strip(),
                "job_filename": filename,
                "registry_source_id": str(source.get("id") or "").strip(),
                "logical_source_id": str(source.get("logical_source_id") or "").strip(),
                "historical_records": linked_records,
                "mixed_provenance_records": mixed_records,
                "distinct_companion_files": len(companion_counts),
                "companion_files": [
                    {"filename": companion, "record_count": count}
                    for companion, count in sorted(
                        companion_counts.items(), key=lambda item: (-item[1], item[0])
                    )
                ],
                "hash_confirmed": False,
                "requires_manual_reconciliation": True,
            }
        )

    return {
        "review_only_alias_candidates": len(candidates),
        "mixed_provenance_records_total": sum(
            candidate["mixed_provenance_records"] for candidate in candidates
        ),
        "candidates": sorted(candidates, key=lambda c: (c["job_id"], c["job_filename"])),
        "record_link_is_exact_source_key_only": True,
        "companion_counts_are_per_record": True,
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

    jobs, sources, records = await asyncio.gather(
        fetch_all(db.private_manual_import_jobs),
        fetch_all(db.private_reference_sources),
        fetch_all(db.private_reference_records),
    )
    print(json.dumps(summarize_failed_alias_mixed_contributors(jobs, sources, records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Failed alias mixed contributor audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
