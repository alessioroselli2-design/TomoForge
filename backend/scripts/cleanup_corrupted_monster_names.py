#!/usr/bin/env python3
"""Guarded cleanup for the four confirmed corrupted monster-name OCR rows.

Default mode is preview-only. The script can perform two explicit mutation
phases, each requiring ``--execute`` plus its own exact confirmation token:

1. ``isolate``: reversible. Exact targets move from ``verified`` to
   ``needs_review`` and receive ``corrupted_entity_name`` plus
   ``corrupted_entity_name_purge_ready``.
2. ``purge``: irreversible. Refuses to run unless all four exact targets are
   already isolated by phase 1, then deletes only those sealed IDs.

Targets are sealed by exact ID, exact name, exact source_text_checksum, count,
and MD5 fingerprint. No regex/name discovery is used for mutation selection.
The 22 source-guided repairable monsters are outside this target set.
"""

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

from services.ocr_semantic_gates import (
    CORRUPTED_ENTITY_NAME_FLAG,
    monster_identity_sanity_flags,
)

EXPECTED_TARGET_COUNT = 4
EXPECTED_TARGET_IDS_MD5 = "c2d920337b602197a7c3f2b2add66a57"
PURGE_READY_FLAG = "corrupted_entity_name_purge_ready"
ISOLATE_CONFIRMATION_TOKEN = (
    "ISOLATE-CORRUPTED-NAMES-4-c2d920337b602197a7c3f2b2add66a57"
)
PURGE_CONFIRMATION_TOKEN = (
    "PURGE-CORRUPTED-NAMES-4-c2d920337b602197a7c3f2b2add66a57"
)

TARGETS: tuple[dict[str, str], ...] = (
    {
        "id": "ref_1fdf6653ef495aeb9ef7c885ac19819e",
        "name": "U R Lo D I G U E R Ra D E L S I G N O R E D E Lla G U E R R A",
        "source_text_checksum": "6dfa02f4cd4dcc7f4021c2db945eb2cf4dc937e8a77d7ee54ba7fb798788f08f",
    },
    {
        "id": "ref_2b8e0286c82d504db812918fa8667129",
        "name": "M:::,, $S$",
        "source_text_checksum": "cc1e5e9635c6e0f280a2e226e7d57b13cc4adc2b0f719fa619276efedd89ab8c",
    },
    {
        "id": "ref_c6b6845d774f52d3ab8c87dfb17cab5d",
        "name": "Fo R M E P R E S C E Lte D E L L1A Rc I D R U I Do",
        "source_text_checksum": "124eaad72090d3066bd2d4771e3dc54f2f28716575ee62a3d0d36e3a4d8a46db",
    },
    {
        "id": "ref_e67bc597b57b5f4daa4febe8e490b0fe",
        "name": "Pec U L I A R Ità D E L Lac E R Ato R E G R I G I O",
        "source_text_checksum": "7fbd1ed39ef35f025b4834ee0b79f7a3f80ed447f204844c5c703bec8a82d490",
    },
)


def _ids_md5(rows: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> str:
    joined = ",".join(sorted(str(row["id"]) for row in rows))
    return hashlib.md5(
        joined.encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()


if len(TARGETS) != EXPECTED_TARGET_COUNT or _ids_md5(TARGETS) != EXPECTED_TARGET_IDS_MD5:
    raise RuntimeError("Sealed corrupted-name target constants are internally inconsistent")


def _state(row: dict[str, Any]) -> str:
    status = str(row.get("review_status") or "")
    flags = {str(flag) for flag in (row.get("review_flags") or [])}
    if status == "verified" and PURGE_READY_FLAG not in flags:
        return "verified"
    if (
        status == "needs_review"
        and CORRUPTED_ENTITY_NAME_FLAG in flags
        and PURGE_READY_FLAG in flags
    ):
        return "isolated"
    return "unexpected"


async def _load_exact_targets(collection: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for expected in TARGETS:
        row = await collection.find_one({"id": expected["id"]})
        if row is None:
            raise RuntimeError(f"Target missing: {expected['id']}")
        if str(row.get("name") or "") != expected["name"]:
            raise RuntimeError(
                f"Target name drift for {expected['id']}: "
                f"expected={expected['name']!r} got={row.get('name')!r}"
            )
        if str(row.get("reference_type") or "") != "monster":
            raise RuntimeError(f"Target is no longer a monster: {expected['id']}")
        if str(row.get("source_text_checksum") or "") != expected["source_text_checksum"]:
            raise RuntimeError(f"Target checksum drift: {expected['id']}")
        if row.get("canonical_id"):
            raise RuntimeError(f"Target linked to canonical data: {expected['id']}")
        if CORRUPTED_ENTITY_NAME_FLAG not in monster_identity_sanity_flags(row.get("name")):
            raise RuntimeError(f"Target no longer fails identity sanity gate: {expected['id']}")
        if _state(row) == "unexpected":
            raise RuntimeError(
                f"Unexpected review state for {expected['id']}: "
                f"status={row.get('review_status')!r} flags={row.get('review_flags')!r}"
            )
        rows.append(row)

    if len(rows) != EXPECTED_TARGET_COUNT or _ids_md5(rows) != EXPECTED_TARGET_IDS_MD5:
        raise RuntimeError("Exact target count/fingerprint drift")
    return rows


async def _isolate(collection: Any, rows: list[dict[str, Any]]) -> int:
    changed = 0
    for snapshot in rows:
        if _state(snapshot) == "isolated":
            continue
        flags = {str(flag) for flag in (snapshot.get("review_flags") or [])}
        flags.update({CORRUPTED_ENTITY_NAME_FLAG, PURGE_READY_FLAG})
        result = await collection.update_one(
            {
                "id": str(snapshot["id"]),
                "review_status": "verified",
                "source_text_checksum": str(snapshot["source_text_checksum"]),
            },
            {"$set": {
                "review_status": "needs_review",
                "review_flags": sorted(flags),
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        if result.matched_count != 1:
            raise RuntimeError(
                f"Isolation affected {result.matched_count} rows for {snapshot['id']}"
            )
        verify = await collection.find_one({"id": str(snapshot["id"])})
        if verify is None or _state(verify) != "isolated":
            raise RuntimeError(f"Isolation post-verification failed: {snapshot['id']}")
        changed += 1
    return changed


async def _purge(collection: Any, rows: list[dict[str, Any]]) -> int:
    if any(_state(row) != "isolated" for row in rows):
        raise RuntimeError("Refusing purge: all four targets must be isolated first")

    # Final live re-read immediately before the single DELETE statement.
    final_rows = await _load_exact_targets(collection)
    if any(_state(row) != "isolated" for row in final_rows):
        raise RuntimeError("Refusing purge: isolated state drifted before DELETE")

    ids = sorted(str(row["id"]) for row in final_rows)
    checksums = sorted(str(row["source_text_checksum"]) for row in final_rows)
    result = (
        collection.client.table(collection.name)
        .delete()
        .in_("id", ids)
        .in_("source_text_checksum", checksums)
        .eq("review_status", "needs_review")
        .execute()
    )
    deleted_ids = {str(row.get("id")) for row in (result.data or [])}
    if deleted_ids != set(ids):
        raise RuntimeError(
            "DELETE result mismatch: "
            f"expected exact IDs={ids!r}, returned={sorted(deleted_ids)!r}"
        )

    for record_id in ids:
        if await collection.find_one({"id": record_id}) is not None:
            raise RuntimeError(f"Post-delete verification found surviving target: {record_id}")
    return len(deleted_ids)


def _preview(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "dry_run": True,
        "target_count": len(rows),
        "target_ids_md5": _ids_md5(rows),
        "targets": [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "state": _state(row),
                "review_status": row.get("review_status"),
                "review_flags": row.get("review_flags") or [],
                "canonical_id": row.get("canonical_id"),
            }
            for row in rows
        ],
        "writes_performed": 0,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guarded corrupted monster-name cleanup")
    parser.add_argument(
        "--action",
        choices=("preview", "isolate", "purge"),
        default="preview",
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    collection = db.private_reference_records
    rows = await _load_exact_targets(collection)

    if args.action == "preview" or not args.execute:
        print("FINAL_REPORT")
        print(json.dumps(_preview(rows), ensure_ascii=False, sort_keys=True))
        return 0

    if args.action == "isolate":
        if args.confirm != ISOLATE_CONFIRMATION_TOKEN:
            raise RuntimeError("Refusing isolation: confirmation token mismatch")
        changed = await _isolate(collection, rows)
        verify_rows = await _load_exact_targets(collection)
        report = {
            "action": "isolate",
            "database_write_completed": True,
            "targets": EXPECTED_TARGET_COUNT,
            "changed_this_run": changed,
            "isolated_total": sum(_state(row) == "isolated" for row in verify_rows),
            "deleted": 0,
        }
    elif args.action == "purge":
        if args.confirm != PURGE_CONFIRMATION_TOKEN:
            raise RuntimeError("Refusing purge: confirmation token mismatch")
        deleted = await _purge(collection, rows)
        report = {
            "action": "purge",
            "database_write_completed": True,
            "targets": EXPECTED_TARGET_COUNT,
            "deleted": deleted,
            "survivors": 0,
        }
    else:
        raise AssertionError(f"Unhandled action: {args.action}")

    print("FINAL_REPORT")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run(_parse_args()))
    except Exception as exc:
        print(f"Corrupted-name cleanup aborted: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
