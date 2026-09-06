#!/usr/bin/env python3
"""Build a deterministic, read-only logical-source backfill plan.

The planner never writes to Supabase. It only proposes updates for records that:
- do not already carry any logical_source_id in source_refs;
- have filename hints;
- resolve, after the existing deterministic filename normalization, to exactly
  one catalogued logical_source_id.

Ambiguous, unmatched, malformed, or already-provenanced records remain excluded.
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

from scripts.audit_logical_source_coverage import (  # noqa: E402
    _candidate_ids_for_filenames,
    _catalog_ids_by_filename,
    _filenames_from_record,
    _logical_source_ids_from_record,
    fetch_all,
)


def build_backfill_plan(records: list[dict], sources: list[dict]) -> dict:
    """Return deterministic candidates plus exclusion counts without applying them."""
    normalized_catalog = _catalog_ids_by_filename(sources, normalized=True)
    candidates: list[dict[str, str]] = []
    excluded_existing = 0
    excluded_no_filename = 0
    excluded_ambiguous = 0
    excluded_unmatched = 0
    excluded_missing_record_id = 0

    for record in records:
        if _logical_source_ids_from_record(record):
            excluded_existing += 1
            continue

        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            excluded_missing_record_id += 1
            continue

        filenames = _filenames_from_record(record)
        if not filenames:
            excluded_no_filename += 1
            continue

        candidate_ids = _candidate_ids_for_filenames(
            filenames, normalized_catalog, normalized=True
        )
        if len(candidate_ids) == 1:
            candidates.append(
                {
                    "record_id": record_id.strip(),
                    "logical_source_id": next(iter(candidate_ids)),
                }
            )
        elif len(candidate_ids) > 1:
            excluded_ambiguous += 1
        else:
            excluded_unmatched += 1

    candidates.sort(key=lambda row: (row["record_id"], row["logical_source_id"]))
    proposed_ids = [row["record_id"] for row in candidates]

    return {
        "mode": "dry_run",
        "writes_performed": 0,
        "records_total": len(records),
        "proposed_backfills": len(candidates),
        "excluded_existing_provenance": excluded_existing,
        "excluded_missing_record_id": excluded_missing_record_id,
        "excluded_no_filename": excluded_no_filename,
        "excluded_ambiguous": excluded_ambiguous,
        "excluded_unmatched": excluded_unmatched,
        "candidate_record_ids_unique": len(proposed_ids) == len(set(proposed_ids)),
        "candidates": candidates,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records, sources = await asyncio.gather(
        fetch_all(db.private_reference_records),
        fetch_all(db.private_reference_sources),
    )
    print(json.dumps(build_backfill_plan(records, sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Logical-source backfill dry-run failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
