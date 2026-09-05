#!/usr/bin/env python3
"""Read-only aggregate audit for logical-source provenance coverage.

This audit reports counts only. It never prints source identifiers, filenames,
reference text, or document contents, and it performs no database writes.
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


async def fetch_all(collection: Any, page_size: int = 1000) -> list[dict]:
    """Read a collection in bounded pages so API row limits cannot truncate audits."""
    rows: list[dict] = []
    offset = 0
    while True:
        page = await collection.find({}).to_list(page_size, offset=offset)
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += len(page)


def _logical_source_ids_from_record(record: dict) -> set[str]:
    refs = record.get("source_refs")
    if not isinstance(refs, list):
        return set()

    result: set[str] = set()
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        value = ref.get("logical_source_id")
        if isinstance(value, str) and value.strip():
            result.add(value.strip())
    return result


def summarize_logical_source_coverage(records: list[dict], sources: list[dict]) -> dict:
    """Return provenance-coverage aggregates without exposing source identifiers."""
    catalog_ids = {
        value.strip()
        for source in sources
        if isinstance((value := source.get("logical_source_id")), str) and value.strip()
    }

    records_with_id = 0
    records_without_id = 0
    records_with_multiple_ids = 0
    records_only_known_ids = 0
    records_with_unknown_ids = 0
    referenced_ids: set[str] = set()
    unknown_ids: set[str] = set()

    for record in records:
        ids = _logical_source_ids_from_record(record)
        if not ids:
            records_without_id += 1
            continue

        records_with_id += 1
        if len(ids) > 1:
            records_with_multiple_ids += 1

        referenced_ids.update(ids)
        missing = ids - catalog_ids
        if missing:
            records_with_unknown_ids += 1
            unknown_ids.update(missing)
        else:
            records_only_known_ids += 1

    total = len(records)
    coverage_ratio = round(records_with_id / total, 4) if total else 0.0

    return {
        "records_total": total,
        "records_with_logical_source_id": records_with_id,
        "records_without_logical_source_id": records_without_id,
        "records_with_multiple_logical_source_ids": records_with_multiple_ids,
        "records_with_only_catalogued_logical_source_ids": records_only_known_ids,
        "records_with_unknown_logical_source_ids": records_with_unknown_ids,
        "logical_source_record_coverage_ratio": coverage_ratio,
        "catalog_logical_source_ids": len(catalog_ids),
        "referenced_logical_source_ids": len(referenced_ids),
        "unknown_referenced_logical_source_ids": len(unknown_ids),
        "logical_source_references_resolve": not unknown_ids,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records, sources = await asyncio.gather(
        fetch_all(db.private_reference_records),
        fetch_all(db.private_reference_sources),
    )
    print(json.dumps(summarize_logical_source_coverage(records, sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Logical-source coverage audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
