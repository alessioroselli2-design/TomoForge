#!/usr/bin/env python3
"""Read-only audit of exact registry SHA peers for zero-import vision sources.

This narrows the unresolved zero-import backlog using only registry metadata.
An exact SHA peer, including an excluded duplicate row, is diagnostic provenance
evidence only. It does not prove that usable text exists and never authorizes
OCR, external processing, import, database writes, review-state changes, or
canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from typing import Any

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all
from scripts.audit_shared_physical_source_slices import (
    _blocked_zero_import_source,
    summarize_shared_physical_source_slices,
)


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _same_logical_full_range(source: dict, peer: dict) -> bool:
    """Require matching logical identity and complete physical range metadata."""
    logical_id = _norm(source.get("logical_source_id"))
    if not logical_id or logical_id != _norm(peer.get("logical_source_id")):
        return False

    source_pages = _int_or_none(source.get("physical_pages"))
    peer_pages = _int_or_none(peer.get("physical_pages"))
    source_start = _int_or_none(source.get("page_start"))
    source_end = _int_or_none(source.get("page_end"))
    peer_start = _int_or_none(peer.get("page_start"))
    peer_end = _int_or_none(peer.get("page_end"))

    if not source_pages or source_pages != peer_pages:
        return False
    if (source_start, source_end) != (1, source_pages):
        return False
    if (peer_start, peer_end) != (1, peer_pages):
        return False

    source_size = _int_or_none(source.get("physical_size_bytes"))
    peer_size = _int_or_none(peer.get("physical_size_bytes"))
    return source_size is not None and source_size == peer_size


def summarize_zero_import_registry_sha_peers(sources: list[dict]) -> dict[str, Any]:
    blocked = [source for source in sources if _blocked_zero_import_source(source)]
    slice_summary = summarize_shared_physical_source_slices(sources)
    slice_ids = set(slice_summary["source_ids_in_shared_physical_artifact_disjoint_slices"])
    residual = [source for source in blocked if str(source.get("id")) not in slice_ids]

    by_sha: dict[str, list[dict]] = defaultdict(list)
    for source in sources:
        sha = _norm(source.get("physical_sha256"))
        if sha:
            by_sha[sha].append(source)

    with_any_peer_ids: list[str] = []
    with_imported_peer_ids: list[str] = []
    with_exact_excluded_duplicate_peer_ids: list[str] = []
    without_peer_ids: list[str] = []

    for source in residual:
        source_id = str(source.get("id") or "").strip()
        sha = _norm(source.get("physical_sha256"))
        peers = [peer for peer in by_sha.get(sha, []) if str(peer.get("id") or "") != source_id]

        if peers:
            with_any_peer_ids.append(source_id)
        else:
            without_peer_ids.append(source_id)

        if any(_int_or_none(peer.get("imported_record_count")) not in (None, 0) for peer in peers):
            with_imported_peer_ids.append(source_id)

        exact_excluded_duplicate = any(
            _norm(peer.get("source_status")) == "duplicate"
            and _norm(peer.get("import_state")) == "excluded"
            and _same_logical_full_range(source, peer)
            for peer in peers
        )
        if exact_excluded_duplicate:
            with_exact_excluded_duplicate_peer_ids.append(source_id)

    explained_duplicate_set = set(with_exact_excluded_duplicate_peer_ids)
    still_unexplained_ids = sorted(
        str(source.get("id"))
        for source in residual
        if str(source.get("id")) not in explained_duplicate_set
    )

    return {
        "zero_import_vision_sources_total": len(blocked),
        "sources_excluded_as_verified_shared_slices": len(slice_ids),
        "residual_zero_import_sources_after_shared_slices": len(residual),
        "residual_sources_with_exact_registry_sha_peer": len(with_any_peer_ids),
        "residual_sources_with_imported_registry_sha_peer": len(with_imported_peer_ids),
        "residual_sources_with_exact_excluded_duplicate_peer": len(
            with_exact_excluded_duplicate_peer_ids
        ),
        "residual_sources_without_exact_registry_sha_peer": len(without_peer_ids),
        "residual_sources_still_unexplained_after_duplicate_peer_evidence": len(
            still_unexplained_ids
        ),
        "source_ids_with_exact_registry_sha_peer": sorted(with_any_peer_ids),
        "source_ids_with_imported_registry_sha_peer": sorted(with_imported_peer_ids),
        "source_ids_with_exact_excluded_duplicate_peer": sorted(
            with_exact_excluded_duplicate_peer_ids
        ),
        "source_ids_without_exact_registry_sha_peer": sorted(without_peer_ids),
        "source_ids_still_unexplained_after_duplicate_peer_evidence": still_unexplained_ids,
        "sha_peer_evidence_is_diagnostic_only": True,
        "excluded_duplicate_peer_does_not_prove_usable_text": True,
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
    print(json.dumps(summarize_zero_import_registry_sha_peers(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Zero-import registry SHA peer audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
