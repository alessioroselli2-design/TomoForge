#!/usr/bin/env python3
"""Read-only repository-artifact audit for concordant text peers.

The audit scans committed structured JSON artifacts only. Exact physical SHA
matches are reported as provenance-review evidence; filename/title matches are
reported separately as weak hints and never promoted to import proof.

No OCR, external processing, database write, review-state mutation, import, or
canonicalization is authorized by this audit.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Iterable

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all
from scripts.audit_zero_import_logical_source_peers import (
    _norm,
    summarize_zero_import_logical_source_peers,
)


def _iter_scalar_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value.strip()
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_scalar_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_scalar_strings(child)


def load_structured_artifact_strings(root: Path) -> dict[str, set[str]]:
    """Load scalar strings from committed JSON artifacts below ``root``."""
    result: dict[str, set[str]] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        result[str(path)] = {text for text in _iter_scalar_strings(payload) if text}
    return result


def summarize_concordant_text_peer_repo_artifacts(
    sources: list[dict],
    jobs: list[dict] | None,
    artifact_strings: dict[str, set[str]],
) -> dict[str, Any]:
    logical = summarize_zero_import_logical_source_peers(sources, jobs)
    concordant_map = logical["structurally_concordant_text_peer_ids_by_source"]
    source_by_id = {str(source.get("id") or "").strip(): source for source in sources}

    exact_sha_paths: dict[str, list[str]] = {}
    filename_paths: dict[str, list[str]] = {}
    title_paths: dict[str, list[str]] = {}

    for blocked_id, peer_ids in concordant_map.items():
        for peer_id in peer_ids:
            peer = source_by_id.get(peer_id, {})
            peer_sha = str(peer.get("physical_sha256") or "").strip()
            peer_filename = str(peer.get("physical_filename") or "").strip()
            peer_title = str(peer.get("title") or "").strip()
            key = f"{blocked_id}->{peer_id}"

            sha_hits = sorted(
                path for path, strings in artifact_strings.items() if peer_sha and peer_sha in strings
            )
            filename_hits = sorted(
                path
                for path, strings in artifact_strings.items()
                if peer_filename and peer_filename in strings
            )
            title_hits = sorted(
                path for path, strings in artifact_strings.items() if peer_title and peer_title in strings
            )

            if sha_hits:
                exact_sha_paths[key] = sha_hits
            if filename_hits:
                filename_paths[key] = filename_hits
            if title_hits:
                title_paths[key] = title_hits

    return {
        "concordant_text_peer_pairs": sum(len(v) for v in concordant_map.values()),
        "pairs_with_exact_sha_structured_artifact": len(exact_sha_paths),
        "pairs_with_filename_only_or_additional_hint": len(filename_paths),
        "pairs_with_title_only_or_additional_hint": len(title_paths),
        "exact_sha_artifact_paths_by_pair": dict(sorted(exact_sha_paths.items())),
        "filename_artifact_paths_by_pair": dict(sorted(filename_paths.items())),
        "title_artifact_paths_by_pair": dict(sorted(title_paths.items())),
        "structured_artifact_files_scanned": len(artifact_strings),
        "exact_sha_artifact_evidence_is_review_candidate_only": True,
        "filename_or_title_evidence_is_not_import_proof": True,
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

    sources, jobs = await asyncio.gather(
        fetch_all(db.private_reference_sources),
        fetch_all(db.private_manual_import_jobs),
    )
    artifact_strings = load_structured_artifact_strings(REPO_ROOT / ".agents" / "outputs")
    print(
        json.dumps(
            summarize_concordant_text_peer_repo_artifacts(sources, jobs, artifact_strings),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Concordant text-peer repository artifact audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
