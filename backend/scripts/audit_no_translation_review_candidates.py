#!/usr/bin/env python3
"""Read-only audit for Italian unresolved records that require no translation.

The report exposes aggregate review-status/reference-type/provenance readiness
counts only. It never prints source text, record names, filenames, user data, or
performs writes.
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

from scripts.audit_reference_readiness import fetch_all


def summarize_candidates(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize locally reviewable unresolved records without exposing content."""
    by_status: dict[str, Counter[str]] = {}
    provenance_gaps: Counter[str] = Counter()
    total = 0
    provenance_ready_total = 0

    for row in records:
        review_status = str(row.get("review_status") or "unknown")
        if review_status == "verified":
            continue
        if str(row.get("source_language") or "unknown") != "it":
            continue
        if str(row.get("translation_status") or "unknown") != "not_required":
            continue

        reference_type = str(row.get("reference_type") or "unknown")
        by_status.setdefault(review_status, Counter())[reference_type] += 1
        total += 1

        has_source_key = bool(row.get("source_key"))
        has_source_refs = bool(row.get("source_refs"))
        if has_source_key and has_source_refs:
            provenance_ready_total += 1
        else:
            if not has_source_key:
                provenance_gaps["missing_source_key"] += 1
            if not has_source_refs:
                provenance_gaps["missing_source_refs"] += 1

    breakdown = {
        status: dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
        for status, counts in sorted(by_status.items())
    }

    return {
        "candidate_total": total,
        "candidate_by_review_status_and_reference_type": breakdown,
        "provenance_ready_total": provenance_ready_total,
        "provenance_gap_counts": dict(sorted(provenance_gaps.items())),
        "reconciled": sum(sum(types.values()) for types in breakdown.values()) == total,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records = await fetch_all(db.private_reference_records)
    print(json.dumps(summarize_candidates(records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"No-translation candidate audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
