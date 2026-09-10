#!/usr/bin/env python3
"""Read-only coverage audit for active vision/mixed registry sources.

This audit only reports how many active, catalogued sources marked `vision_required`
or `mixed` have any imported records according to registry metadata. It never runs
OCR, retries imports, writes to Supabase, mutates review state, or authorizes
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

from scripts.audit_manual_import_readiness import fetch_all


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def summarize_vision_import_coverage(sources: list[dict[str, Any]]) -> dict[str, Any]:
    eligible: list[dict[str, Any]] = []
    for source in sources:
        if _norm(source.get("source_status")) != "active":
            continue
        if _norm(source.get("import_state")) != "catalogued":
            continue
        if _norm(source.get("text_mode")) not in {"vision_required", "mixed"}:
            continue
        eligible.append(source)

    by_mode_total: Counter[str] = Counter()
    by_mode_with_imports: Counter[str] = Counter()
    zero_import_ids: list[str] = []
    with_import_ids: list[str] = []

    for source in eligible:
        mode = _norm(source.get("text_mode"))
        by_mode_total[mode] += 1
        imported = int(source.get("imported_record_count") or 0)
        source_id = str(source.get("id") or "").strip()
        if imported > 0:
            by_mode_with_imports[mode] += 1
            if source_id:
                with_import_ids.append(source_id)
        elif source_id:
            zero_import_ids.append(source_id)

    total = len(eligible)
    with_imports = sum(by_mode_with_imports.values())
    zero_imports = total - with_imports
    coverage_ratio = (with_imports / total) if total else None

    return {
        "active_catalogued_vision_or_mixed_sources": total,
        "sources_with_imported_records": with_imports,
        "sources_with_zero_imported_records": zero_imports,
        "coverage_ratio": coverage_ratio,
        "coverage_percent": round(coverage_ratio * 100, 2) if coverage_ratio is not None else None,
        "by_text_mode": {
            mode: {
                "sources": by_mode_total[mode],
                "with_imported_records": by_mode_with_imports[mode],
                "zero_imported_records": by_mode_total[mode] - by_mode_with_imports[mode],
            }
            for mode in sorted(by_mode_total)
        },
        "source_ids_with_imported_records": sorted(with_import_ids),
        "source_ids_with_zero_imported_records": sorted(zero_import_ids),
        "parser_ocr_coverage_gate_clear": total == 0 or zero_imports == 0,
        "registry_import_count_is_coverage_evidence_only": True,
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
    print(json.dumps(summarize_vision_import_coverage(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Vision import coverage audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
