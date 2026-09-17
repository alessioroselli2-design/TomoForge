#!/usr/bin/env python3
"""Dry-run audit for legacy verified private reference records.

This script is intentionally READ-ONLY. It selects legacy rows currently marked
``review_status='verified'`` from ``private_reference_records``, applies the
current OCR semantic/numeric gates in memory, and prints what *would* require
review. It never inserts, updates, deletes, upserts, canonicalizes, or changes
review state in Supabase.

Why scan every verified row instead of filtering on an old OCR flag?
The legacy auto-approval path could have produced verified OCR records without
retaining a useful OCR review flag. Scanning all verified rows is therefore the
fail-closed audit strategy; semantic/numeric anomaly gates only affect monster
records.
"""

from __future__ import annotations

import ast
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.ocr_semantic_gates import (
    CA_FORMAT_ERROR_FLAG,
    CA_OUT_OF_BOUNDS_FLAG,
    HP_FORMAT_ERROR_FLAG,
    apply_ocr_review_gates,
)

DRY_RUN_ONLY = True
PAGE_SIZE = 1000

# Defense in depth: fail before opening a DB connection if a future edit adds a
# mutation call to this script. Strings in this set are data, not method calls.
_FORBIDDEN_DB_MUTATION_ATTRS = frozenset({
    "insert",
    "insert_one",
    "insert_many",
    "update",
    "update_one",
    "update_many",
    "upsert",
    "delete",
    "delete_one",
    "delete_many",
    "replace_one",
    "rpc",
})

_GATE_FAILURE_FLAGS = frozenset({
    CA_OUT_OF_BOUNDS_FLAG,
    CA_FORMAT_ERROR_FLAG,
    HP_FORMAT_ERROR_FLAG,
})


def _assert_source_is_read_only() -> None:
    """Refuse to run if this file contains a known DB mutation method call."""
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(__file__))
    found = sorted({
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in _FORBIDDEN_DB_MUTATION_ATTRS
    })
    if found:
        raise RuntimeError(
            "Dry-run safety check failed: database mutation calls detected: "
            + ", ".join(found)
        )


async def _fetch_verified_records(collection: Any, page_size: int = PAGE_SIZE) -> list[dict]:
    """Read every verified row in bounded pages; this function performs SELECT only."""
    rows: list[dict] = []
    offset = 0
    while True:
        page = await collection.find({"review_status": "verified"}).to_list(
            page_size,
            offset=offset,
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += len(page)


def _safe_name(record: dict[str, Any]) -> str:
    """Return a printable record name without terminal control characters."""
    name = str(record.get("name") or record.get("normalized_name") or "<senza nome>")
    return "".join(ch for ch in name if ch.isprintable()).strip() or "<senza nome>"


def analyze_verified_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply OCR gates in memory and return a deterministic dry-run report."""
    failures: list[dict[str, Any]] = []
    healthy = 0
    monsters = 0

    for record in records:
        if record.get("reference_type") == "monster":
            monsters += 1

        # In-memory only: this returns a copy and never persists anything.
        gated = apply_ocr_review_gates(record)
        activated = sorted(
            flag
            for flag in set(gated.get("review_flags") or [])
            if flag in _GATE_FAILURE_FLAGS
        )

        if activated:
            failures.append({
                "name": _safe_name(record),
                "reference_type": str(record.get("reference_type") or "other"),
                "flags": activated,
                "would_review_status": str(gated.get("review_status") or "pending"),
            })
        else:
            healthy += 1

    failures.sort(key=lambda item: (item["name"].casefold(), item["reference_type"]))
    return {
        "dry_run": True,
        "database_writes_performed": 0,
        "verified_records_analyzed": len(records),
        "verified_monsters_analyzed": monsters,
        "semantic_numeric_healthy": healthy,
        "semantic_numeric_failed": len(failures),
        "failed_records": failures,
    }


def _print_report(report: dict[str, Any]) -> None:
    print("TOMOFORGE LEGACY VERIFIED RECORD AUDIT — DRY-RUN")
    print("Database writes performed: 0")
    print(f"Verified records analyzed: {report['verified_records_analyzed']}")
    print(f"Verified monsters analyzed: {report['verified_monsters_analyzed']}")
    print(f"Healthy against semantic/numeric gates: {report['semantic_numeric_healthy']}")
    print(f"Failed semantic/numeric gates: {report['semantic_numeric_failed']}")
    print()
    print("Records that would be sent back to review:")
    if not report["failed_records"]:
        print("- none")
    else:
        for failure in report["failed_records"]:
            print(f"- {failure['name']} -> {', '.join(failure['flags'])}")

    # Machine-readable copy for CI/artifacts. Contains no mutation instructions.
    print()
    print("JSON_REPORT")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


async def _run() -> int:
    if not DRY_RUN_ONLY:
        raise RuntimeError("Refusing to run: DRY_RUN_ONLY must remain True")

    # Execute before importing/configuring the database connection.
    _assert_source_is_read_only()

    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records = await _fetch_verified_records(db.private_reference_records)
    report = analyze_verified_records(records)
    _print_report(report)
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Legacy record dry-run audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
