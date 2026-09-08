#!/usr/bin/env python3
"""Read-only audit for reference-source rows sharing the same physical SHA-256.

Shared physical files can be legitimate compilations split into non-overlapping
logical sources, or duplicate registry rows for the same logical source. This
audit classifies those cases without authorizing deletion, retry, OCR, registry
writes, or canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all


def _non_overlapping_ranges(rows: list[dict]) -> bool:
    ranges: list[tuple[int, int]] = []
    for row in rows:
        start, end = row.get("page_start"), row.get("page_end")
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
            return False
        ranges.append((start, end))
    ranges.sort()
    return all(previous[1] < current[0] for previous, current in zip(ranges, ranges[1:]))


def summarize_reference_source_sha_groups(sources: list[dict]) -> dict[str, Any]:
    by_sha: dict[str, list[dict]] = defaultdict(list)
    for source in sources:
        sha = str(source.get("physical_sha256") or "").strip().lower()
        if sha:
            by_sha[sha].append(source)

    groups: list[dict[str, Any]] = []
    counts = {
        "shared_sha_groups_total": 0,
        "same_logical_source_duplicates": 0,
        "split_compilations_non_overlapping": 0,
        "shared_sha_needs_review": 0,
    }

    for sha, rows in sorted(by_sha.items()):
        if len(rows) < 2:
            continue
        counts["shared_sha_groups_total"] += 1
        logical_ids = {str(row.get("logical_source_id") or "").strip() for row in rows}
        logical_ids.discard("")

        if len(logical_ids) == 1:
            classification = "same_logical_source_duplicate"
            counts["same_logical_source_duplicates"] += 1
        elif len(logical_ids) > 1 and _non_overlapping_ranges(rows):
            classification = "split_compilation_non_overlapping"
            counts["split_compilations_non_overlapping"] += 1
        else:
            classification = "shared_sha_needs_review"
            counts["shared_sha_needs_review"] += 1

        groups.append(
            {
                "physical_sha256": sha,
                "classification": classification,
                "source_ids": sorted(str(row.get("id")) for row in rows),
                "logical_source_ids": sorted(logical_ids),
            }
        )

    return {
        **counts,
        "groups": groups,
        "evidence_is_diagnostic_only": True,
        "database_write_authorized": False,
        "source_deletion_authorized": False,
        "automatic_retry_authorized": False,
        "ocr_generation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    sources = await fetch_all(db.private_reference_sources)
    print(json.dumps(summarize_reference_source_sha_groups(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Reference source SHA audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
