#!/usr/bin/env python3
"""Read-only audit of logical-source peers for unresolved zero-import vision sources.

This audit starts only after the shared-physical-slice and exact-SHA duplicate
triage. A matching ``logical_source_id`` is diagnostic provenance evidence, not
proof that two physical copies are interchangeable. In particular, a text-mode
peer can identify a potentially cheaper review path, but it never authorizes an
import, OCR, external processing, review-state mutation, or canonicalization.
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
from scripts.audit_zero_import_registry_sha_peers import (
    _int_or_none,
    _norm,
    summarize_zero_import_registry_sha_peers,
)


def _is_text_peer_candidate(peer: dict) -> bool:
    """Return whether a logical peer is a live/catalogued text-capable candidate."""
    return (
        _norm(peer.get("text_mode")) == "text"
        and _norm(peer.get("source_status")) in {"active", "superseded"}
        and _norm(peer.get("import_state")) in {"catalogued", "imported"}
    )


def summarize_zero_import_logical_source_peers(sources: list[dict]) -> dict[str, Any]:
    sha_summary = summarize_zero_import_registry_sha_peers(sources)
    unresolved_ids = set(
        sha_summary["source_ids_still_unexplained_after_duplicate_peer_evidence"]
    )
    unresolved = [
        source for source in sources if str(source.get("id") or "").strip() in unresolved_ids
    ]

    by_logical_id: dict[str, list[dict]] = defaultdict(list)
    for source in sources:
        logical_id = _norm(source.get("logical_source_id"))
        if logical_id:
            by_logical_id[logical_id].append(source)

    with_any_peer_ids: list[str] = []
    with_text_peer_ids: list[str] = []
    with_imported_peer_ids: list[str] = []
    without_peer_ids: list[str] = []
    text_peer_map: dict[str, list[str]] = {}

    for source in unresolved:
        source_id = str(source.get("id") or "").strip()
        logical_id = _norm(source.get("logical_source_id"))
        peers = [
            peer
            for peer in by_logical_id.get(logical_id, [])
            if str(peer.get("id") or "").strip() != source_id
        ]

        if peers:
            with_any_peer_ids.append(source_id)
        else:
            without_peer_ids.append(source_id)

        text_peers = [peer for peer in peers if _is_text_peer_candidate(peer)]
        if text_peers:
            with_text_peer_ids.append(source_id)
            text_peer_map[source_id] = sorted(
                str(peer.get("id") or "").strip() for peer in text_peers
            )

        if any(_int_or_none(peer.get("imported_record_count")) not in (None, 0) for peer in peers):
            with_imported_peer_ids.append(source_id)

    return {
        "zero_import_vision_sources_total": sha_summary["zero_import_vision_sources_total"],
        "sources_excluded_as_verified_shared_slices": sha_summary[
            "sources_excluded_as_verified_shared_slices"
        ],
        "sources_explained_by_exact_excluded_duplicate_peer": sha_summary[
            "residual_sources_with_exact_excluded_duplicate_peer"
        ],
        "residual_sources_entering_logical_peer_triage": len(unresolved),
        "residual_sources_with_same_logical_source_peer": len(with_any_peer_ids),
        "residual_sources_with_text_mode_logical_peer": len(with_text_peer_ids),
        "residual_sources_with_imported_logical_peer": len(with_imported_peer_ids),
        "residual_sources_without_same_logical_source_peer": len(without_peer_ids),
        "source_ids_with_same_logical_source_peer": sorted(with_any_peer_ids),
        "source_ids_with_text_mode_logical_peer": sorted(with_text_peer_ids),
        "source_ids_with_imported_logical_peer": sorted(with_imported_peer_ids),
        "source_ids_without_same_logical_source_peer": sorted(without_peer_ids),
        "text_mode_logical_peer_ids_by_source": dict(sorted(text_peer_map.items())),
        "logical_source_match_is_diagnostic_only": True,
        "text_mode_peer_does_not_prove_interchangeable_content": True,
        "text_mode_peer_requires_provenance_review": True,
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
    print(json.dumps(summarize_zero_import_logical_source_peers(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Zero-import logical-source peer audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
