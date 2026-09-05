#!/usr/bin/env python3
"""Read-only aggregate audit for logical-source provenance coverage.

This audit reports counts only. It never prints source identifiers, filenames,
reference text, or document contents, and it performs no database writes.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


async def fetch_all(collection: Any, page_size: int = 1000) -> list[dict]:
    """Read a collection in bounded pages so API row limits cannot truncate audits."""
    rows: list[dict] = []
    offset = 0
    while True:
        page = await collection.find({}).to_list(page_size, offset=offset)
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += len(page)


def _logical_source_ids_from_record(record: dict) -> set[str]:
    refs = record.get("source_refs")
    if not isinstance(refs, list):
        return set()

    result: set[str] = set()
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        value = ref.get("logical_source_id")
        if isinstance(value, str) and value.strip():
            result.add(value.strip())
    return result


def _filenames_from_record(record: dict) -> set[str]:
    refs = record.get("source_refs")
    if not isinstance(refs, list):
        return set()

    result: set[str] = set()
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        value = ref.get("filename")
        if isinstance(value, str) and value.strip():
            result.add(value.strip())
    return result


def _normalize_filename_key(value: str) -> str:
    """Normalize only deterministic transport noise, never semantic title words."""
    name = value.strip().replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"\.[^.]+$", "", name)
    name = re.sub(r"[_-]\d{10,}$", "", name)
    name = re.sub(r"\s*\(\d+\)$", "", name)
    decomposed = unicodedata.normalize("NFKD", name).casefold()
    return "".join(char for char in decomposed if char.isalnum())


def _catalog_ids_by_filename(sources: list[dict], *, normalized: bool = False) -> dict[str, set[str]]:
    """Map catalogue filenames to logical IDs without exposing either in output."""
    result: dict[str, set[str]] = {}
    for source in sources:
        logical_id = source.get("logical_source_id")
        if not isinstance(logical_id, str) or not logical_id.strip():
            continue
        logical_id = logical_id.strip()

        for key in ("physical_filename", "filename"):
            filename = source.get(key)
            if not isinstance(filename, str) or not filename.strip():
                continue
            lookup_key = _normalize_filename_key(filename) if normalized else filename.strip()
            if lookup_key:
                result.setdefault(lookup_key, set()).add(logical_id)
    return result


def _candidate_ids_for_filenames(
    filenames: set[str], catalog: dict[str, set[str]], *, normalized: bool = False
) -> set[str]:
    candidate_ids: set[str] = set()
    for filename in filenames:
        lookup_key = _normalize_filename_key(filename) if normalized else filename
        candidate_ids.update(catalog.get(lookup_key, set()))
    return candidate_ids


def summarize_logical_source_coverage(records: list[dict], sources: list[dict]) -> dict:
    """Return provenance-coverage aggregates without exposing source identifiers."""
    catalog_ids = {
        value.strip()
        for source in sources
        if isinstance((value := source.get("logical_source_id")), str) and value.strip()
    }
    exact_catalog = _catalog_ids_by_filename(sources)
    normalized_catalog = _catalog_ids_by_filename(sources, normalized=True)

    records_with_id = 0
    records_without_id = 0
    records_with_multiple_ids = 0
    records_only_known_ids = 0
    records_with_unknown_ids = 0
    records_without_id_with_filename_hint = 0
    records_without_id_without_filename_hint = 0
    exact_unique = exact_ambiguous = exact_unmatched = 0
    normalized_unique = normalized_ambiguous = normalized_unmatched = 0
    referenced_ids: set[str] = set()
    unknown_ids: set[str] = set()

    for record in records:
        ids = _logical_source_ids_from_record(record)
        if not ids:
            records_without_id += 1
            filenames = _filenames_from_record(record)
            if not filenames:
                records_without_id_without_filename_hint += 1
                continue

            records_without_id_with_filename_hint += 1
            exact_candidates = _candidate_ids_for_filenames(filenames, exact_catalog)
            if len(exact_candidates) == 1:
                exact_unique += 1
            elif len(exact_candidates) > 1:
                exact_ambiguous += 1
            else:
                exact_unmatched += 1

            normalized_candidates = _candidate_ids_for_filenames(
                filenames, normalized_catalog, normalized=True
            )
            if len(normalized_candidates) == 1:
                normalized_unique += 1
            elif len(normalized_candidates) > 1:
                normalized_ambiguous += 1
            else:
                normalized_unmatched += 1
            continue

        records_with_id += 1
        if len(ids) > 1:
            records_with_multiple_ids += 1

        referenced_ids.update(ids)
        missing = ids - catalog_ids
        if missing:
            records_with_unknown_ids += 1
            unknown_ids.update(missing)
        else:
            records_only_known_ids += 1

    total = len(records)
    coverage_ratio = round(records_with_id / total, 4) if total else 0.0

    return {
        "records_total": total,
        "records_with_logical_source_id": records_with_id,
        "records_without_logical_source_id": records_without_id,
        "records_with_multiple_logical_source_ids": records_with_multiple_ids,
        "records_with_only_catalogued_logical_source_ids": records_only_known_ids,
        "records_with_unknown_logical_source_ids": records_with_unknown_ids,
        "records_without_id_with_filename_hint": records_without_id_with_filename_hint,
        "records_without_id_without_filename_hint": records_without_id_without_filename_hint,
        "records_without_id_with_unique_filename_match": exact_unique,
        "records_without_id_with_ambiguous_filename_match": exact_ambiguous,
        "records_without_id_with_unmatched_filename": exact_unmatched,
        "records_without_id_with_unique_normalized_filename_match": normalized_unique,
        "records_without_id_with_ambiguous_normalized_filename_match": normalized_ambiguous,
        "records_without_id_with_unmatched_normalized_filename": normalized_unmatched,
        "logical_source_record_coverage_ratio": coverage_ratio,
        "catalog_logical_source_ids": len(catalog_ids),
        "referenced_logical_source_ids": len(referenced_ids),
        "unknown_referenced_logical_source_ids": len(unknown_ids),
        "logical_source_references_resolve": not unknown_ids,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records, sources = await asyncio.gather(
        fetch_all(db.private_reference_records),
        fetch_all(db.private_reference_sources),
    )
    print(json.dumps(summarize_logical_source_coverage(records, sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Logical-source coverage audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
