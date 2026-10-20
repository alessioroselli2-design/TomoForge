#!/usr/bin/env python3
"""Guarded isolation of one reviewed legacy structural false positive."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TARGET_ID = "ref_d4932158a65058b3ba0cc76480da33d5"
TARGET_NAME = "Conosci Il Tuo Nemico"
TARGET_FILENAME = "Manuale_del_giocatore__1787259882002.pdf"
ISOLATION_FLAG = "legacy_structural_false_positive_isolated"
CONFIRMATION_TOKEN = "ISOLATE-STRUCTURAL-FALSE-POSITIVE-CONOSCI-IL-TUO-NEMICO"


def _source_filename(row: dict[str, Any]) -> str:
    refs = row.get("source_refs") or []
    filenames = {
        str(ref.get("filename") or "")
        for ref in refs
        if isinstance(ref, dict) and ref.get("filename")
    }
    if filenames != {TARGET_FILENAME}:
        raise RuntimeError(f"Target source provenance drift: {sorted(filenames)!r}")
    return TARGET_FILENAME


async def _load_target(collection: Any) -> dict[str, Any]:
    row = await collection.find_one({"id": TARGET_ID})
    if row is None:
        raise RuntimeError("Target record missing")
    expected = {
        "name": TARGET_NAME,
        "reference_type": "monster",
        "review_status": "verified",
    }
    for field, value in expected.items():
        if str(row.get(field) or "") != value:
            raise RuntimeError(f"Target {field} drift: {row.get(field)!r}")
    existing_flags = {str(flag) for flag in (row.get("review_flags") or [])}
    allowed_failure_flags = {
        "CA_format_error",
        "CA_out_of_bounds",
        "HP_format_error",
        "ocr_da_verificare",
    }
    if not existing_flags or not existing_flags.issubset(allowed_failure_flags):
        raise RuntimeError(
            f"Target has unexpected pre-isolation review flags: {sorted(existing_flags)!r}"
        )
    if row.get("canonical_id"):
        raise RuntimeError("Target is linked to canonical data")
    if not str(row.get("source_text_checksum") or ""):
        raise RuntimeError("Target has no source_text_checksum")
    _source_filename(row)
    return row


async def _isolate(collection: Any, snapshot: dict[str, Any]) -> None:
    result = await collection.update_one(
        {
            "id": TARGET_ID,
            "name": TARGET_NAME,
            "reference_type": "monster",
            "review_status": "verified",
            "source_text_checksum": str(snapshot["source_text_checksum"]),
        },
        {
            "$set": {
                "review_status": "needs_review",
                "review_flags": [ISOLATION_FLAG],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    if result.matched_count != 1:
        raise RuntimeError(f"Isolation matched {result.matched_count} records")
    verify = await collection.find_one({"id": TARGET_ID})
    if verify is None:
        raise RuntimeError("Target disappeared after isolation")
    if str(verify.get("review_status") or "") != "needs_review":
        raise RuntimeError("Post-isolation review_status mismatch")
    if list(verify.get("review_flags") or []) != [ISOLATION_FLAG]:
        raise RuntimeError("Post-isolation review_flags mismatch")


async def _run(args: argparse.Namespace) -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    row = await _load_target(db.private_reference_records)
    if args.execute:
        if args.confirm != CONFIRMATION_TOKEN:
            raise RuntimeError("Refusing isolation: confirmation token mismatch")
        await _isolate(db.private_reference_records, row)
    print("FINAL_REPORT")
    print(
        json.dumps(
            {
                "database_write_completed": bool(args.execute),
                "dry_run": not args.execute,
                "record_id": TARGET_ID,
                "name": TARGET_NAME,
                "source_filename": TARGET_FILENAME,
                "source_text_checksum": row["source_text_checksum"],
                "review_status": "needs_review"
                if args.execute
                else row["review_status"],
                "review_flags": [ISOLATION_FLAG]
                if args.execute
                else row["review_flags"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    return asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
