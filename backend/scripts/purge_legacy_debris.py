#!/usr/bin/env python3
"""Guarded live cleanup for the legacy OCR debris confirmed on 2026-09-17.

This script is intentionally separate from ``repair_legacy_records.py`` so the
legacy audit remains permanently read-only.

No mutation happens unless BOTH ``--execute`` and the exact confirmation token
are supplied. Before any write it recomputes the delete target from live data,
requires the expected count/fingerprint, validates the nine structural-table
IDs/names, and aborts on any drift.

Execution order is safety-oriented:
1. preflight all targets;
2. isolate the nine structural tables (non-destructive, idempotent updates);
3. only if every table is isolated, delete the exact 94 verified debris rows in
   one PostgREST DELETE statement;
4. verify deleted rows are gone and tables are still present/isolated.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.ocr_semantic_gates import (
    INVALID_ENTITY_TITLE_FLAG,
    entity_name_semantic_flags,
)

EXPECTED_DELETE_COUNT = 94
EXPECTED_DELETE_IDS_MD5 = "203cb5e825490842f5ad8354ff077156"
EXPECTED_ISOLATE_COUNT = 9
EXPECTED_ISOLATE_IDS_MD5 = "11874c95f40e05c96267a8c07091e135"
STRUCTURAL_TABLE_FLAG = "structural_table_isolated"
PAGE_SIZE = 1000
CONFIRMATION_TOKEN = (
    "PURGE-94-203cb5e825490842f5ad8354ff077156-"
    "ISOLATE-9-11874c95f40e05c96267a8c07091e135"
)

# Exact live snapshot of the nine tables explicitly excluded from DELETE.
# These IDs allow an interrupted isolation phase to be resumed safely without
# broad name matching or loss of already-applied review state.
STRUCTURAL_TABLE_TARGETS: tuple[tuple[str, str], ...] = (
    ("ref_60dce1f703e85daba89fa8c97d40e183", "Tabell A Degli Oggetti Magici C"),
    ("ref_017e3c2763bb5ff19d3e8102628e4599", "Tabell A Degli Oggetti Magici D"),
    ("ref_66116d7d95b954519deea455ef03c3dc", "Tabell A Degli Oggetti Magici E"),
    ("ref_c940967245db57708914eaa2ec05a368", "Tabell A Degli Oggetti Magici F"),
    ("ref_11d2a3e3498750aea89afff3dac4cdae", "Tabell A Degli Oggetti Magici G"),
    ("ref_57734a99be1357418ad233f1c4b62913", "Tabell A Degli Oggetti Magici H"),
    ("ref_1b5a86cd62e55f66832ef9b09218bea5", "Tabell A Degli Oggetti Magici I"),
    ("ref_d37a199b90e15976838d20fd13aa3be9", "Tabella Degli Oggetti Magici A"),
    ("ref_2eca343f989a5b669c44a4ebe96ba6bb", "Tabella Degli Oggetti Magici B"),
)


def _compact_entity_name(name: Any) -> str:
    text = unicodedata.normalize("NFKD", str(name or ""))
    ascii_text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", ascii_text.casefold())


def _heading_family(name: Any) -> str | None:
    """Classify only names already accepted by Entity_Name_Semantic_Gate."""
    if INVALID_ENTITY_TITLE_FLAG not in entity_name_semantic_flags(name):
        return None

    compact = _compact_entity_name(name)
    if compact.startswith("capitolo"):
        return "capitolo"
    if compact.startswith("appendice"):
        return "appendice"
    if re.match(r"^passo\d+", compact):
        return "passo"
    if compact.startswith("tabella"):
        return "tabella"
    if compact.startswith("statistichedeimostri"):
        return "statistiche_dei_mostri"
    return None


def _ids_md5(rows: list[dict[str, Any]]) -> str:
    joined = ",".join(sorted(str(row["id"]) for row in rows))
    return hashlib.md5(joined.encode("utf-8"), usedforsecurity=False).hexdigest()


async def _fetch_verified_records(collection: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = await collection.find({"review_status": "verified"}).to_list(
            PAGE_SIZE,
            offset=offset,
        )
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += len(page)


def _select_delete_targets(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only the 8 false monsters + 86 chapter/appendix/step debris."""
    targets: list[dict[str, Any]] = []

    for record in records:
        family = _heading_family(record.get("name"))
        if family is None:
            continue

        reference_type = str(record.get("reference_type") or "")
        if reference_type == "monster":
            # The eight previously confirmed false-monster headings.
            targets.append(record)
        elif family in {"capitolo", "appendice", "passo"}:
            # The 86 confirmed non-monster heading/step debris rows.
            targets.append(record)

    return targets


async def _load_structural_tables(collection: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record_id, expected_name in STRUCTURAL_TABLE_TARGETS:
        row = await collection.find_one({"id": record_id})
        if row is None:
            raise RuntimeError(
                f"Structural table missing: {record_id} / {expected_name}"
            )
        if str(row.get("name") or "") != expected_name:
            raise RuntimeError(
                f"Structural table name drift for {record_id}: "
                f"expected {expected_name!r}, got {row.get('name')!r}"
            )
        if str(row.get("reference_type") or "") == "monster":
            raise RuntimeError(
                f"Structural table unexpectedly typed as monster: {record_id}"
            )
        if _heading_family(expected_name) != "tabella":
            raise RuntimeError(
                f"Structural table no longer matches table gate: {expected_name}"
            )
        rows.append(row)
    return rows


async def _preflight(
    collection: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    verified = await _fetch_verified_records(collection)
    delete_targets = _select_delete_targets(verified)
    isolate_targets = await _load_structural_tables(collection)

    delete_ids = {str(row["id"]) for row in delete_targets}
    isolate_ids = {str(row["id"]) for row in isolate_targets}
    overlap = sorted(delete_ids & isolate_ids)
    if overlap:
        raise RuntimeError(f"DELETE/isolation target overlap: {overlap}")

    delete_md5 = _ids_md5(delete_targets)
    isolate_md5 = _ids_md5(isolate_targets)

    if (
        len(delete_targets) != EXPECTED_DELETE_COUNT
        or delete_md5 != EXPECTED_DELETE_IDS_MD5
    ):
        raise RuntimeError(
            "DELETE target drift detected: "
            f"count={len(delete_targets)} md5={delete_md5}; "
            f"expected count={EXPECTED_DELETE_COUNT} md5={EXPECTED_DELETE_IDS_MD5}"
        )
    if (
        len(isolate_targets) != EXPECTED_ISOLATE_COUNT
        or isolate_md5 != EXPECTED_ISOLATE_IDS_MD5
    ):
        raise RuntimeError(
            "Isolation target drift detected: "
            f"count={len(isolate_targets)} md5={isolate_md5}; "
            f"expected count={EXPECTED_ISOLATE_COUNT} md5={EXPECTED_ISOLATE_IDS_MD5}"
        )

    # Tables may already be isolated after an interrupted safe retry; any other
    # status is unexpected and aborts before DELETE.
    for row in isolate_targets:
        status = str(row.get("review_status") or "")
        flags = {str(flag) for flag in (row.get("review_flags") or [])}
        already_isolated = status == "needs_review" and STRUCTURAL_TABLE_FLAG in flags
        if status != "verified" and not already_isolated:
            raise RuntimeError(
                f"Unexpected structural-table state for {row['id']}: "
                f"status={status!r}, flags={sorted(flags)!r}"
            )

    return delete_targets, isolate_targets


async def _isolate_structural_tables(
    collection: Any, rows: list[dict[str, Any]]
) -> int:
    """Preserve each table row and its existing flags; only add isolation state."""
    changed = 0
    for snapshot in rows:
        record_id = str(snapshot["id"])
        current = await collection.find_one({"id": record_id})
        if current is None:
            raise RuntimeError(
                f"Structural table disappeared before update: {record_id}"
            )

        flags = {str(flag) for flag in (current.get("review_flags") or [])}
        status = str(current.get("review_status") or "")
        if status == "needs_review" and STRUCTURAL_TABLE_FLAG in flags:
            continue
        if status != "verified":
            raise RuntimeError(
                f"Structural table state changed before update: {record_id} status={status!r}"
            )

        flags.add(STRUCTURAL_TABLE_FLAG)
        result = await collection.update_one(
            {"id": record_id, "review_status": "verified"},
            {
                "$set": {
                    "review_status": "needs_review",
                    "review_flags": sorted(flags),
                }
            },
        )
        if result.matched_count != 1:
            raise RuntimeError(
                f"Structural table update affected {result.matched_count} rows: {record_id}"
            )
        changed += 1

        verify = await collection.find_one({"id": record_id})
        verify_flags = {
            str(flag) for flag in ((verify or {}).get("review_flags") or [])
        }
        if (
            not verify
            or verify.get("review_status") != "needs_review"
            or STRUCTURAL_TABLE_FLAG not in verify_flags
        ):
            raise RuntimeError(
                f"Structural table post-update verification failed: {record_id}"
            )

    return changed


def _delete_confirmed_debris(collection: Any, rows: list[dict[str, Any]]) -> int:
    """Delete the exact preflighted 94 IDs in one database statement."""
    ids = sorted(str(row["id"]) for row in rows)
    if len(ids) != EXPECTED_DELETE_COUNT or _ids_md5(rows) != EXPECTED_DELETE_IDS_MD5:
        raise RuntimeError(
            "Refusing DELETE: in-memory target no longer matches sealed snapshot"
        )

    result = (
        collection.client.table(collection.name)
        .delete()
        .in_("id", ids)
        .eq("review_status", "verified")
        .execute()
    )
    deleted_ids = {str(row.get("id")) for row in (result.data or [])}
    if deleted_ids != set(ids):
        raise RuntimeError(
            "DELETE result mismatch: "
            f"expected {len(ids)} exact IDs, database returned {len(deleted_ids)}"
        )
    return len(deleted_ids)


async def _verify_final_state(
    collection: Any,
    delete_rows: list[dict[str, Any]],
    table_rows: list[dict[str, Any]],
) -> None:
    remaining_deleted = []
    for row in delete_rows:
        if await collection.find_one({"id": str(row["id"])}) is not None:
            remaining_deleted.append(str(row["id"]))
    if remaining_deleted:
        raise RuntimeError(
            f"Post-delete verification found surviving debris: {remaining_deleted}"
        )

    for snapshot in table_rows:
        row = await collection.find_one({"id": str(snapshot["id"])})
        flags = {str(flag) for flag in ((row or {}).get("review_flags") or [])}
        if (
            not row
            or row.get("review_status") != "needs_review"
            or STRUCTURAL_TABLE_FLAG not in flags
        ):
            raise RuntimeError(
                f"Structural table final verification failed: {snapshot['id']}"
            )


def _print_plan(
    delete_rows: list[dict[str, Any]], table_rows: list[dict[str, Any]]
) -> None:
    print("TOMOFORGE LEGACY DEBRIS PURGE — GUARDED EXECUTOR")
    print(f"DELETE targets sealed: {len(delete_rows)} ({_ids_md5(delete_rows)})")
    print(f"Structural tables sealed: {len(table_rows)} ({_ids_md5(table_rows)})")
    print(
        "Structural tables are excluded from DELETE and retain existing review flags."
    )
    print("No write occurs without --execute plus the exact confirmation token.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute", action="store_true", help="Perform the guarded live writes"
    )
    parser.add_argument("--confirm", default="", help="Exact sealed confirmation token")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    collection = db.private_reference_records
    delete_rows, table_rows = await _preflight(collection)
    _print_plan(delete_rows, table_rows)

    if not args.execute:
        print("PREVIEW ONLY: database writes performed: 0")
        return 0
    if args.confirm != CONFIRMATION_TOKEN:
        raise RuntimeError(
            "Refusing execution: confirmation token does not match sealed target"
        )

    isolated_now = await _isolate_structural_tables(collection, table_rows)

    # Re-run destructive-target preflight AFTER the table updates and BEFORE
    # DELETE. Table isolation cannot affect the sealed 94-row delete fingerprint.
    verified_after_isolation = await _fetch_verified_records(collection)
    delete_rows_after_isolation = _select_delete_targets(verified_after_isolation)
    if (
        len(delete_rows_after_isolation) != EXPECTED_DELETE_COUNT
        or _ids_md5(delete_rows_after_isolation) != EXPECTED_DELETE_IDS_MD5
    ):
        raise RuntimeError(
            "DELETE target drift after table isolation; no DELETE performed"
        )

    deleted = _delete_confirmed_debris(collection, delete_rows_after_isolation)
    await _verify_final_state(collection, delete_rows_after_isolation, table_rows)

    report = {
        "database_write_completed": True,
        "deleted_legacy_debris": deleted,
        "structural_tables_isolated": EXPECTED_ISOLATE_COUNT,
        "structural_tables_changed_this_run": isolated_now,
        "structural_tables_deleted": 0,
        "final_message": f"{deleted} record eliminati, {EXPECTED_ISOLATE_COUNT} tabelle isolate",
    }
    print("FINAL_REPORT")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run(_parse_args()))
    except Exception as exc:
        print(f"Legacy debris purge aborted: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
