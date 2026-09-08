#!/usr/bin/env python3
"""Read-only audit for active catalogued sources that require vision/OCR but have no imported records.

The result is a review gate only. It never authorizes OCR, external processing,
import retries, database writes, review-state changes, or canonicalization.
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

from scripts.audit_manual_import_readiness import fetch_all


def summarize_catalogued_vision_zero_import(sources: list[dict]) -> dict[str, Any]:
    blocked_ids: list[str] = []
    examined = 0
    for source in sources:
        if str(source.get("source_status") or "") != "active":
            continue
        if str(source.get("import_state") or "") != "catalogued":
            continue
        if str(source.get("text_mode") or "") not in {"vision_required", "mixed"}:
            continue
        examined += 1
        imported = source.get("imported_record_count")
        if imported in (None, 0):
            source_id = str(source.get("id") or "").strip()
            if source_id:
                blocked_ids.append(source_id)

    return {
        "active_catalogued_vision_sources_examined": examined,
        "active_catalogued_vision_sources_with_zero_imported_records": len(blocked_ids),
        "blocked_source_ids": sorted(blocked_ids),
        "requires_authorized_text_extraction_before_import": bool(blocked_ids),
        "evidence_is_diagnostic_only": True,
        "ocr_authorized": False,
        "external_processing_authorized": False,
        "automatic_import_authorized": False,
        "database_write_authorized": False,
        "review_state_mutation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    sources = await fetch_all(db.private_reference_sources)
    print(json.dumps(summarize_catalogued_vision_zero_import(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Vision zero-import audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
