#!/usr/bin/env python3
"""Read-only verification of the already-applied Abishai Rosso repair."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TARGET_ID = "ref_36a7ca03ed43517b8b036334ea6d61ec"
TARGET_NAME = "Abishai Rosso"
TARGET_CHECKSUM = "1a5e1be53072a007e52d28739e4eeb08edeb8560ee8510b0db53b24b5a7df858"
EXPECTED_CORE = {
    "classe_armatura": "22 (armatura naturale)",
    "punti_ferita": "289 (34d8 + 136)",
    "velocita": "9 m, volare 15m",
}
EXPECTED_FLAGS = ["ocr_da_verificare", "source_guided_repair"]


async def verify_live_state(collection):
    row = await collection.find_one({"id": TARGET_ID})
    if row is None:
        raise RuntimeError("Repaired target missing")
    expected_scalars = {
        "name": TARGET_NAME,
        "reference_type": "monster",
        "review_status": "pending",
        "source_text_checksum": TARGET_CHECKSUM,
    }
    for field, expected in expected_scalars.items():
        if str(row.get(field) or "") != expected:
            raise RuntimeError(f"Repaired target {field} mismatch")
    if sorted(str(flag) for flag in (row.get("review_flags") or [])) != sorted(
        EXPECTED_FLAGS
    ):
        raise RuntimeError("Repaired target review_flags mismatch")
    if row.get("canonical_id"):
        raise RuntimeError("Repaired target unexpectedly linked to canonical data")
    if not list(row.get("source_refs") or []):
        raise RuntimeError("Repaired target provenance missing")
    attributes = row.get("attributes") or {}
    for field, expected in EXPECTED_CORE.items():
        if str(attributes.get(field) or "") != expected:
            raise RuntimeError(f"Repaired target core mismatch: {field}")
    if not str(row.get("updated_at") or ""):
        raise RuntimeError("Repaired target updated_at missing")
    return row


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    row = await verify_live_state(db.private_reference_records)
    print("FINAL_REPORT")
    print(
        json.dumps(
            {
                "database_write_completed": False,
                "verified_live_update": True,
                "record_id": row["id"],
                "name": row["name"],
                "attributes": {
                    field: row["attributes"][field] for field in EXPECTED_CORE
                },
                "review_status": row["review_status"],
                "review_flags": row["review_flags"],
                "updated_at": row["updated_at"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
