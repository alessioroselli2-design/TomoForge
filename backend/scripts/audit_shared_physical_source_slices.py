#!/usr/bin/env python3
"""Read-only audit for live sources that share one physical artifact.

A repeated physical filename is not necessarily a duplicate source row. A single
PDF can intentionally carry several logical sources on disjoint page ranges.
This audit identifies that structural pattern without changing source identity
or authorizing import, OCR, database writes, review changes, or canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all


def _blocked_zero_import_source(source: dict) -> bool:
    return (
        str(source.get("source_status") or "") == "active"
        and str(source.get("import_state") or "") == "catalogued"
        and str(source.get("text_mode") or "") in {"vision_required", "mixed"}
        and source.get("imported_record_count") in (None, 0)
        and bool(str(source.get("id") or "").strip())
    )


def _physical_key(source: dict) -> tuple[str, str]:
    filename = Path(str(source.get("physical_filename") or "").strip()).name.casefold()
    sha = str(source.get("physical_sha256") or "").strip().casefold()
    return filename, sha


def _valid_slice(source: dict) -> tuple[int, int] | None:
    try:
        start = int(source.get("page_start") or 0)
        end = int(source.get("page_end") or 0)
        pages = int(source.get("physical_pages") or 0)
    except (TypeError, ValueError):
        return None
    if start < 1 or end < start or pages < 1 or end > pages:
        return None
    return start, end


def summarize_shared_physical_source_slices(sources: list[dict]) -> dict[str, Any]:
    blocked = [source for source in sources if _blocked_zero_import_source(source)]
    blocked_source_ids = sorted(str(source.get("id")) for source in blocked)
    by_filename: dict[str, list[dict]] = defaultdict(list)
    for source in blocked:
        filename, _ = _physical_key(source)
        if filename:
            by_filename[filename].append(source)

    repeated_filename_groups = [group for group in by_filename.values() if len(group) > 1]
    repeated_source_ids = sorted(
        str(source.get("id")) for group in repeated_filename_groups for source in group
    )

    shared_slice_group_count = 0
    shared_slice_source_ids: list[str] = []
    unresolved_group_count = 0
    unresolved_source_ids: list[str] = []

    for group in repeated_filename_groups:
        shas = {str(source.get("physical_sha256") or "").strip().casefold() for source in group}
        sizes = {source.get("physical_size_bytes") for source in group}
        page_counts = {source.get("physical_pages") for source in group}
        logical_ids = [str(source.get("logical_source_id") or "").strip() for source in group]
        slices = [_valid_slice(source) for source in group]

        same_physical_artifact = (
            len(shas) == 1
            and "" not in shas
            and len(sizes) == 1
            and None not in sizes
            and len(page_counts) == 1
            and None not in page_counts
        )
        unique_logical_sources = (
            all(logical_ids) and len(set(logical_ids)) == len(logical_ids)
        )
        valid_slices = all(value is not None for value in slices)
        sorted_slices = sorted(value for value in slices if value is not None)
        non_overlapping = valid_slices and all(
            previous[1] < current[0]
            for previous, current in zip(sorted_slices, sorted_slices[1:])
        )

        ids = sorted(str(source.get("id")) for source in group)
        if same_physical_artifact and unique_logical_sources and non_overlapping:
            shared_slice_group_count += 1
            shared_slice_source_ids.extend(ids)
        else:
            unresolved_group_count += 1
            unresolved_source_ids.extend(ids)

    repeated_id_set = set(repeated_source_ids)
    shared_slice_id_set = set(shared_slice_source_ids)
    unique_filename_source_ids = sorted(
        source_id for source_id in blocked_source_ids if source_id not in repeated_id_set
    )
    physical_layout_unexplained_source_ids = sorted(
        source_id for source_id in blocked_source_ids if source_id not in shared_slice_id_set
    )

    return {
        "zero_import_vision_sources_total": len(blocked),
        "repeated_physical_filename_group_count": len(repeated_filename_groups),
        "repeated_physical_filename_source_count": len(repeated_source_ids),
        "shared_physical_artifact_disjoint_slice_group_count": shared_slice_group_count,
        "shared_physical_artifact_disjoint_slice_source_count": len(shared_slice_source_ids),
        "unique_physical_filename_source_count": len(unique_filename_source_ids),
        "physical_layout_explained_by_shared_slices_source_count": len(shared_slice_source_ids),
        "physical_layout_unexplained_source_count": len(physical_layout_unexplained_source_ids),
        "unresolved_repeated_physical_identity_group_count": unresolved_group_count,
        "unresolved_repeated_physical_identity_source_count": len(unresolved_source_ids),
        "source_ids_with_repeated_physical_filename": repeated_source_ids,
        "source_ids_in_shared_physical_artifact_disjoint_slices": sorted(shared_slice_source_ids),
        "source_ids_with_unique_physical_filename": unique_filename_source_ids,
        "source_ids_with_unexplained_physical_layout": physical_layout_unexplained_source_ids,
        "source_ids_with_unresolved_repeated_physical_identity": sorted(unresolved_source_ids),
        "physical_layout_explanation_is_not_provenance_resolution": True,
        "shared_physical_slices_are_diagnostic_only": True,
        "shared_physical_slices_do_not_authorize_import": True,
        "shared_physical_slices_do_not_resolve_logical_provenance": True,
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
    print(json.dumps(summarize_shared_physical_source_slices(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Shared physical source slice audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
