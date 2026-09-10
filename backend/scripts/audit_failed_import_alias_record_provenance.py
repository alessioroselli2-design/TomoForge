#!/usr/bin/env python3
"""Read-only audit of historical record provenance for failed alias candidates.

The audit is deliberately conservative: it only considers failed
``manual_source_missing`` jobs that have one filename-alias registry candidate
with a non-matching content hash. Historical records are linked only through an
exact ``source_key == job filename`` match. It then measures whether each
record's source_refs actually mentions that filename and whether those refs are
exclusive to that file or mixed with other files.

No identity is confirmed from these signals. The result is review-only and
never authorizes retry, writes, OCR, translation, review mutation, or
canonicalization.
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


def _ref_filenames(source_refs: Any) -> set[str]:
    if not isinstance(source_refs, list):
        return set()
    return {
        str(ref.get("filename") or "").strip()
        for ref in source_refs
        if isinstance(ref, dict) and str(ref.get("filename") or "").strip()
    }


def summarize_failed_alias_record_provenance(
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
        key = _normalized_filename_alias_key(filename)
        matches = by_alias.get(key, []) if key else []
        if not filename or len(matches) != 1:
            continue

        source = matches[0]
        job_sha = str(job.get("source_fingerprint") or "").strip().casefold()
        source_sha = str(source.get("physical_sha256") or "").strip().casefold()
        if job_sha and source_sha and job_sha == source_sha:
            continue

        linked = [r for r in records if str(r.get("source_key") or "").strip() == filename]
        refs_mention_job = 0
        refs_exclusive_to_job = 0
        refs_mixed_with_other_files = 0
        refs_missing_filename = 0
        language_matches = 0
        job_language = str(job.get("source_language") or "").strip().casefold()

        for record in linked:
            ref_names = _ref_filenames(record.get("source_refs"))
            if filename in ref_names:
                refs_mention_job += 1
                if ref_names == {filename}:
                    refs_exclusive_to_job += 1
                elif len(ref_names) > 1:
                    refs_mixed_with_other_files += 1
            else:
                refs_missing_filename += 1

            record_language = str(record.get("source_language") or "").strip().casefold()
            if job_language and record_language == job_language:
                language_matches += 1

        candidates.append(
            {
                "job_id": str(job.get("id") or "").strip(),
                "job_filename": filename,
                "registry_source_id": str(source.get("id") or "").strip(),
                "logical_source_id": str(source.get("logical_source_id") or "").strip(),
                "historical_records": len(linked),
                "records_with_job_filename_in_source_refs": refs_mention_job,
                "records_exclusive_to_job_filename": refs_exclusive_to_job,
                "records_with_mixed_file_provenance": refs_mixed_with_other_files,
                "records_missing_job_filename_in_source_refs": refs_missing_filename,
                "records_matching_job_language": language_matches,
                "hash_confirmed": False,
                "requires_manual_reconciliation": True,
            }
        )

    return {
        "review_only_alias_candidates": len(candidates),
        "historical_records_total": sum(c["historical_records"] for c in candidates),
        "records_with_job_filename_in_source_refs": sum(
            c["records_with_job_filename_in_source_refs"] for c in candidates
        ),
        "records_exclusive_to_job_filename": sum(
            c["records_exclusive_to_job_filename"] for c in candidates
        ),
        "records_with_mixed_file_provenance": sum(
            c["records_with_mixed_file_provenance"] for c in candidates
        ),
        "records_missing_job_filename_in_source_refs": sum(
            c["records_missing_job_filename_in_source_refs"] for c in candidates
        ),
        "candidates": sorted(candidates, key=lambda c: (c["job_id"], c["job_filename"])),
        "record_link_is_exact_source_key_only": True,
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
    print(json.dumps(summarize_failed_alias_record_provenance(jobs, sources, records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Failed alias record provenance audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
