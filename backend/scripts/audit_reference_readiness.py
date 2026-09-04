#!/usr/bin/env python3
"""Read-only aggregate readiness audit for the private reference catalogue.

The audit intentionally reports counts and ratios only. It does not expose rule
text, source document contents, user identifiers, or make database writes.
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


def _review_queue_by_reference_type(records: list[dict]) -> dict[str, int]:
    """Return aggregate unresolved counts by reference type without exposing content."""
    queue = Counter()
    for row in records:
        if str(row.get("review_status") or "unknown") == "verified":
            continue
        reference_type = str(row.get("reference_type") or "unknown")
        queue[reference_type] += 1
    return dict(sorted(queue.items(), key=lambda item: (-item[1], item[0])))


def summarize_readiness(records: list[dict], sources: list[dict], canonical: list[dict]) -> dict:
    review = Counter(str(row.get("review_status") or "unknown") for row in records)
    translation = Counter(str(row.get("translation_status") or "unknown") for row in records)
    source_states = Counter(str(row.get("source_status") or "unknown") for row in sources)
    text_modes = Counter(str(row.get("text_mode") or "unknown") for row in sources)
    import_states = Counter(str(row.get("import_state") or "unknown") for row in sources)
    canonical_states = Counter(str(row.get("verification_status") or "unknown") for row in canonical)

    total = len(records)
    verified = review["verified"]
    review_ratio = round(verified / total, 4) if total else 0.0

    return {
        "records_total": total,
        "records_verified": verified,
        "records_needs_review": review["needs_review"],
        "records_pending": review["pending"],
        "review_queue_by_reference_type": _review_queue_by_reference_type(records),
        "translation_failed": translation["failed"],
        "translation_translated": translation["translated"],
        "records_linked_to_canonical": sum(1 for row in records if row.get("canonical_id")),
        "verified_ratio": review_ratio,
        "sources_total": len(sources),
        "sources_active": source_states["active"],
        "sources_duplicate": source_states["duplicate"],
        "sources_superseded": source_states["superseded"],
        "sources_catalogued": import_states["catalogued"],
        "sources_excluded": import_states["excluded"],
        "sources_text": text_modes["text"],
        "sources_mixed": text_modes["mixed"],
        "sources_vision_required": text_modes["vision_required"],
        "canonical_total": len(canonical),
        "canonical_verified": canonical_states["verified"],
        "canonical_needs_review": canonical_states["needs_review"],
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records, sources, canonical = await asyncio.gather(
        fetch_all(db.private_reference_records),
        fetch_all(db.private_reference_sources),
        fetch_all(db.private_reference_canonical),
    )
    print(json.dumps(summarize_readiness(records, sources, canonical), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Reference readiness audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
