#!/usr/bin/env python3
"""Read-only structured-presence audit for active vision/mixed sources.

This audit reports whether registry sources currently have any structured records.
It deliberately does not infer OCR/parser completion from imported record counts.
No OCR, import, retry, Supabase write, review mutation, or canonicalization is run.
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

from scripts.audit_manual_import_readiness import fetch_all


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def summarize_vision_structured_presence(sources: list[dict[str, Any]]) -> dict[str, Any]:
    scoped = [
        source
        for source in sources
        if _norm(source.get("source_status")) == "active"
        and _norm(source.get("import_state")) == "catalogued"
        and _norm(source.get("text_mode")) in {"vision_required", "mixed"}
    ]

    by_mode_total: Counter[str] = Counter()
    by_mode_with_records: Counter[str] = Counter()
    source_ids_with_records: list[str] = []
    source_ids_without_records: list[str] = []

    for source in scoped:
        mode = _norm(source.get("text_mode"))
        by_mode_total[mode] += 1
        source_id = str(source.get("id") or "").strip()
        if int(source.get("imported_record_count") or 0) > 0:
            by_mode_with_records[mode] += 1
            if source_id:
                source_ids_with_records.append(source_id)
        elif source_id:
            source_ids_without_records.append(source_id)

    total = len(scoped)
    with_records = sum(by_mode_with_records.values())
    without_records = total - with_records
    presence_ratio = (with_records / total) if total else None

    return {
        "active_catalogued_vision_or_mixed_sources": total,
        "sources_with_structured_records": with_records,
        "sources_without_structured_records": without_records,
        "structured_presence_ratio": presence_ratio,
        "structured_presence_percent": round(presence_ratio * 100, 2) if presence_ratio is not None else None,
        "by_text_mode": {
            mode: {
                "sources": by_mode_total[mode],
                "with_structured_records": by_mode_with_records[mode],
                "without_structured_records": by_mode_total[mode] - by_mode_with_records[mode],
            }
            for mode in sorted(by_mode_total)
        },
        "source_ids_with_structured_records": sorted(source_ids_with_records),
        "source_ids_without_structured_records": sorted(source_ids_without_records),
        "registry_structured_presence_complete": total == 0 or without_records == 0,
        "parser_ocr_completion_percent": None,
        "parser_ocr_completion_inferable_from_registry_counts": False,
        "parser_ocr_readiness_status": "NOT_INFERABLE_FROM_REGISTRY_COUNTS",
        "ocr_authorized": False,
        "external_processing_authorized": False,
        "automatic_import_authorized": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "review_state_mutation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    sources = await fetch_all(db.private_reference_sources)
    print(json.dumps(summarize_vision_structured_presence(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Vision structured-presence audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
