#!/usr/bin/env python3
"""Dry-run audit for legacy verified private reference records.

This script is intentionally READ-ONLY. It selects legacy rows currently marked
``review_status='verified'`` from ``private_reference_records``, applies the
current OCR semantic/numeric/entity-name gates in memory, and prints what would
require review or removal. It never inserts, updates, deletes, upserts,
canonicalizes, or changes review state in Supabase.
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
    INVALID_ENTITY_TITLE_FLAG,
    apply_ocr_review_gates,
)

DRY_RUN_ONLY = True
PAGE_SIZE = 1000

_FORBIDDEN_DB_MUTATION_ATTRS = frozenset({
    "insert_one",
    "insert_many",
    "update_one",
    "update_many",
    "delete_one",
    "delete_many",
    "replace_one",
    "upsert",
    "execute_sql",
    "apply_migration",
})

_REPAIR_FAILURE_FLAGS = frozenset({
    CA_OUT_OF_BOUNDS_FLAG,
    CA_FORMAT_ERROR_FLAG,
    HP_FORMAT_ERROR_FLAG,
})


class _ReadOnlyCollection:
    """Minimal facade that exposes only the collection read operation we need."""

    __slots__ = ("_collection",)

    def __init__(self, collection: Any) -> None:
        object.__setattr__(self, "_collection", collection)

    def find(self, query: dict[str, Any]) -> Any:
        return object.__getattribute__(self, "_collection").find(query)

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"Dry-run collection exposes no method named {name!r}")


def _assert_source_is_read_only() -> None:
    """Refuse to run if this file contains a known DB persistence method call."""
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


async def _fetch_verified_records(
    collection: _ReadOnlyCollection,
    page_size: int = PAGE_SIZE,
) -> list[dict]:
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
    name = str(record.get("name") or record.get("normalized_name") or "<senza nome>")
    return "".join(ch for ch in name if ch.isprintable()).strip() or "<senza nome>"


def analyze_verified_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify verified legacy rows without changing any source record."""
    ocr_debris: list[dict[str, Any]] = []
    real_repairs: list[dict[str, Any]] = []
    healthy = 0
    monsters = 0

    for record in records:
        if record.get("reference_type") == "monster":
            monsters += 1

        gated = apply_ocr_review_gates(record)
        all_flags = set(gated.get("review_flags") or [])
        repair_flags = sorted(flag for flag in all_flags if flag in _REPAIR_FAILURE_FLAGS)
        invalid_title = INVALID_ENTITY_TITLE_FLAG in all_flags

        item = {
            "name": _safe_name(record),
            "reference_type": str(record.get("reference_type") or "other"),
            "flags": ([INVALID_ENTITY_TITLE_FLAG] if invalid_title else []) + repair_flags,
            "would_review_status": str(gated.get("review_status") or "pending"),
        }

        if invalid_title:
            # A strong heading/title match is classified as OCR debris even if
            # its bogus monster fields also trigger CA/HP errors. That keeps
            # false entities out of the genuine repair queue.
            ocr_debris.append(item)
        elif repair_flags:
            real_repairs.append(item)
        else:
            healthy += 1

    key = lambda item: (item["name"].casefold(), item["reference_type"])
    ocr_debris.sort(key=key)
    real_repairs.sort(key=key)

    return {
        "dry_run": True,
        "database_writes_performed": 0,
        "verified_records_analyzed": len(records),
        "verified_monsters_analyzed": monsters,
        "healthy_records": healthy,
        "ocr_debris_to_eliminate": len(ocr_debris),
        "real_records_to_repair": len(real_repairs),
        "ocr_debris_records": ocr_debris,
        "repair_records": real_repairs,
    }


def _print_report(report: dict[str, Any]) -> None:
    print("TOMOFORGE LEGACY VERIFIED RECORD AUDIT — DRY-RUN")
    print("Database writes performed: 0")
    print(f"Verified records analyzed: {report['verified_records_analyzed']}")
    print(f"Verified monsters analyzed: {report['verified_monsters_analyzed']}")
    print(f"Healthy records: {report['healthy_records']}")
    print(f"Scorie OCR da Eliminare: {report['ocr_debris_to_eliminate']}")
    print(f"Record Reali da Riparare: {report['real_records_to_repair']}")

    print()
    print("Scorie OCR da Eliminare:")
    if not report["ocr_debris_records"]:
        print("- none")
    else:
        for item in report["ocr_debris_records"]:
            print(f"- {item['name']} -> {', '.join(item['flags'])}")

    print()
    print("Record Reali da Riparare:")
    if not report["repair_records"]:
        print("- none")
    else:
        for item in report["repair_records"]:
            print(f"- {item['name']} -> {', '.join(item['flags'])}")

    print()
    print("JSON_REPORT")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


async def _run() -> int:
    if not DRY_RUN_ONLY:
        raise RuntimeError("Refusing to run: DRY_RUN_ONLY must remain True")

    _assert_source_is_read_only()

    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    collection = _ReadOnlyCollection(db.private_reference_records)
    records = await _fetch_verified_records(collection)
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
