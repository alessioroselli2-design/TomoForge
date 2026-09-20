#!/usr/bin/env python3
"""Fail-closed isolation of the three human-reviewed structural false positives."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

ISOLATION_FLAG = "legacy_structural_false_positive_isolated"
EXPECTED_COUNT = 3
EXPECTED_IDS_MD5 = "0476fbdd7bfdb86e76630ea493ad7731"
CONFIRMATION_TOKEN = (
    "ISOLATE-STRUCTURAL-FALSE-POSITIVES-3-0476fbdd7bfdb86e76630ea493ad7731"
)
TARGETS: tuple[dict[str, str], ...] = (
    {"id": "ref_c2a7d3e06e52569e851f737c33260f9d", "name": "Colline"},
    {"id": "ref_51cc5af68a475cb2a7ac137ede8e1cc7", "name": "Di Fuoco"},
    {"id": "ref_9b3fc6257b9f52819f603a4458318743", "name": "Mietitore"},
)
PROTECTED_FIELDS = (
    "name",
    "reference_type",
    "attributes",
    "source_refs",
    "source_text_checksum",
    "canonical_id",
)


def _ids_md5(rows: list[dict[str, Any]]) -> str:
    joined = ",".join(sorted(str(row["id"]) for row in rows))
    return hashlib.md5(joined.encode(), usedforsecurity=False).hexdigest()


def _validate_row(row: dict[str, Any], expected: dict[str, str]) -> None:
    if str(row.get("id") or "") != expected["id"]:
        raise RuntimeError(f"Isolation id drift: {expected['id']}")
    if str(row.get("name") or "") != expected["name"]:
        raise RuntimeError(f"Isolation name drift: {expected['id']}")
    if str(row.get("reference_type") or "") != "monster":
        raise RuntimeError(f"Isolation type drift: {expected['id']}")
    if str(row.get("review_status") or "") != "verified":
        raise RuntimeError(f"Isolation status drift: {expected['id']}")
    if list(row.get("review_flags") or []):
        raise RuntimeError(f"Isolation review flag drift: {expected['id']}")
    if row.get("canonical_id"):
        raise RuntimeError(f"Isolation canonical link detected: {expected['id']}")
    if not str(row.get("source_text_checksum") or ""):
        raise RuntimeError(f"Isolation checksum missing: {expected['id']}")
    if not list(row.get("source_refs") or []):
        raise RuntimeError(f"Isolation provenance missing: {expected['id']}")


async def load_targets(collection: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for expected in TARGETS:
        row = await collection.find_one({"id": expected["id"]})
        if row is None:
            raise RuntimeError(f"Isolation target missing: {expected['id']}")
        _validate_row(row, expected)
        rows.append(row)
    if len(rows) != EXPECTED_COUNT or _ids_md5(rows) != EXPECTED_IDS_MD5:
        raise RuntimeError("Isolation target count/fingerprint drift")
    return rows


async def revalidate_targets(collection: Any, snapshots: list[dict[str, Any]]) -> None:
    for snapshot in snapshots:
        current = await collection.find_one({"id": snapshot["id"]})
        if current != snapshot:
            raise RuntimeError(f"Isolation concurrent drift: {snapshot['id']}")


async def isolate_targets(
    collection: Any, snapshots: list[dict[str, Any]], updated_at: str
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for snapshot in snapshots:
        query = {
            "id": snapshot["id"],
            "name": snapshot["name"],
            "reference_type": "monster",
            "review_status": "verified",
            "review_flags": snapshot.get("review_flags") or [],
            "source_text_checksum": snapshot["source_text_checksum"],
        }
        result = await collection.update_one(
            query,
            {
                "$set": {
                    "review_status": "needs_review",
                    "review_flags": [ISOLATION_FLAG],
                    "updated_at": updated_at,
                }
            },
        )
        if result.matched_count != 1:
            raise RuntimeError(
                f"Isolation matched {result.matched_count} rows for {snapshot['id']}"
            )
        verify = await collection.find_one({"id": snapshot["id"]})
        if verify is None:
            raise RuntimeError(f"Isolation target disappeared: {snapshot['id']}")
        if str(verify.get("review_status") or "") != "needs_review":
            raise RuntimeError(
                f"Isolation status verification failed: {snapshot['id']}"
            )
        if list(verify.get("review_flags") or []) != [ISOLATION_FLAG]:
            raise RuntimeError(f"Isolation flag verification failed: {snapshot['id']}")
        if str(verify.get("updated_at") or "") != updated_at:
            raise RuntimeError(
                f"Isolation timestamp verification failed: {snapshot['id']}"
            )
        for field in PROTECTED_FIELDS:
            if verify.get(field) != snapshot.get(field):
                raise RuntimeError(
                    f"Isolation collateral field change for {snapshot['id']}: {field}"
                )
        results.append(verify)
    return results


async def _run(args: argparse.Namespace) -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    if args.execute and args.confirm != CONFIRMATION_TOKEN:
        raise RuntimeError("Refusing isolation: confirmation token mismatch")

    collection = db.private_reference_records
    snapshots = await load_targets(collection)
    updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows = snapshots
    if args.execute:
        await revalidate_targets(collection, snapshots)
        rows = await isolate_targets(collection, snapshots, updated_at)

    reports = []
    for before, after in zip(snapshots, rows, strict=True):
        reports.append(
            {
                "record_id": before["id"],
                "name": before["name"],
                "executed": bool(args.execute),
                "before": {
                    "review_status": before["review_status"],
                    "review_flags": before.get("review_flags") or [],
                },
                "after": {
                    "review_status": after["review_status"],
                    "review_flags": after.get("review_flags") or [],
                    "updated_at": after.get("updated_at"),
                },
            }
        )
    print("FINAL_REPORT")
    print(
        json.dumps(
            {
                "dry_run": not args.execute,
                "targets": EXPECTED_COUNT,
                "isolated": EXPECTED_COUNT if args.execute else 0,
                "updates_performed": EXPECTED_COUNT if args.execute else 0,
                "batch_updated_at": updated_at if args.execute else None,
                "reports": reports,
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
