#!/usr/bin/env python3
"""Read-only validation for human review-status drift in the reference catalogue."""

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

REVIEW_STATUSES = {"verified", "needs_review", "pending"}


def summarize_review_status_validity(records: list[dict]) -> dict:
    counts = Counter(str(row.get("review_status") or "unknown") for row in records)
    unexpected = {status: count for status, count in counts.items() if status not in REVIEW_STATUSES}
    return {
        "records_total": len(records),
        "review_status_breakdown": dict(sorted(counts.items())),
        "review_status_unexpected_states": dict(sorted(unexpected.items())),
        "review_statuses_valid": not unexpected,
    }


async def fetch_all(collection: Any, page_size: int = 1000) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page = await collection.find({}).to_list(page_size, offset=offset)
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += len(page)


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records = await fetch_all(db.private_reference_records)
    summary = summarize_review_status_validity(records)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["review_statuses_valid"] else 2


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Review-status validity audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
