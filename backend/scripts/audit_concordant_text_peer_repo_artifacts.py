#!/usr/bin/env python3
"""Read-only repository-artifact audit for concordant text peers.

The audit scans committed structured JSON artifacts only. Exact physical SHA
matches are reported as provenance-review evidence; filename/title matches are
reported separately as weak hints and never promoted to import proof. Nominal
hints that point at more than one concordant pair are explicitly marked
ambiguous so they cannot be mistaken for unique provenance evidence. Every
concordant pair is also assigned to exactly one evidence bucket: exact SHA,
unique nominal hint, ambiguous nominal hint, or no repository evidence.

No OCR, external processing, database write, review-state mutation, import, or
canonicalization is authorized by this audit.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
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


def _ambiguous_hint_paths(
    filename_paths: dict[str, list[str]],
    title_paths: dict[str, list[str]],
    exact_sha_paths: dict[str, list[str]],
) -> tuple[dict[str, list[str]], set[str]]:
    """Return nominal artifact paths shared by multiple SHA-unproven pairs.

    A pair with any exact-SHA artifact evidence is deliberately excluded from
    this ambiguity classification: its nominal hits may still be useful for
    review, but they are not the only repository evidence available for that
    pair.
    """
    path_to_pairs: dict[str, set[str]] = defaultdict(set)
    for pair_key, paths in filename_paths.items():
        if pair_key in exact_sha_paths:
            continue
        for path in paths:
            path_to_pairs[path].add(pair_key)
    for pair_key, paths in title_paths.items():
        if pair_key in exact_sha_paths:
            continue
        for path in paths:
            path_to_pairs[path].add(pair_key)

    ambiguous = {
        path: sorted(pair_keys)
        for path, pair_keys in sorted(path_to_pairs.items())
        if len(pair_keys) > 1
    }
    ambiguous_pairs = {pair_key for pair_keys in ambiguous.values() for pair_key in pair_keys}
    return ambiguous, ambiguous_pairs


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
    all_pair_keys: set[str] = set()

    for blocked_id, peer_ids in concordant_map.items():
        for peer_id in peer_ids:
            peer = source_by_id.get(peer_id, {})
            peer_sha = str(peer.get("physical_sha256") or "").strip()
            peer_filename = str(peer.get("physical_filename") or "").strip()
            peer_title = str(peer.get("title") or "").strip()
            key = f"{blocked_id}->{peer_id}"
            all_pair_keys.add(key)

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

    exact_sha_pairs = set(exact_sha_paths)
    nominal_hint_pairs = (set(filename_paths) | set(title_paths)) - exact_sha_pairs
    ambiguous_nominal_paths, ambiguous_nominal_pairs = _ambiguous_hint_paths(
        filename_paths,
        title_paths,
        exact_sha_paths,
    )
    unique_nominal_pairs = nominal_hint_pairs - ambiguous_nominal_pairs
    no_artifact_evidence_pairs = all_pair_keys - exact_sha_pairs - nominal_hint_pairs

    evidence_bucket_total = (
        len(exact_sha_pairs)
        + len(unique_nominal_pairs)
        + len(ambiguous_nominal_pairs)
        + len(no_artifact_evidence_pairs)
    )
    evidence_buckets_are_exhaustive = evidence_bucket_total == len(all_pair_keys)

    return {
        "concordant_text_peer_pairs": len(all_pair_keys),
        "pairs_with_exact_sha_structured_artifact": len(exact_sha_pairs),
        "pairs_with_filename_only_or_additional_hint": len(filename_paths),
        "pairs_with_title_only_or_additional_hint": len(title_paths),
        "pairs_with_nominal_hint_but_no_exact_sha": len(nominal_hint_pairs),
        "pairs_with_unique_nominal_hint": len(unique_nominal_pairs),
        "pairs_with_ambiguous_nominal_hint": len(ambiguous_nominal_pairs),
        "pairs_with_no_repository_artifact_evidence": len(no_artifact_evidence_pairs),
        "exact_sha_pair_ids": sorted(exact_sha_pairs),
        "unique_nominal_hint_pair_ids": sorted(unique_nominal_pairs),
        "ambiguous_nominal_hint_pair_ids": sorted(ambiguous_nominal_pairs),
        "no_repository_artifact_evidence_pair_ids": sorted(no_artifact_evidence_pairs),
        "evidence_buckets_are_exhaustive": evidence_buckets_are_exhaustive,
        "exact_sha_artifact_paths_by_pair": dict(sorted(exact_sha_paths.items())),
        "filename_artifact_paths_by_pair": dict(sorted(filename_paths.items())),
        "title_artifact_paths_by_pair": dict(sorted(title_paths.items())),
        "ambiguous_nominal_artifact_paths": ambiguous_nominal_paths,
        "structured_artifact_files_scanned": len(artifact_strings),
        "exact_sha_artifact_evidence_is_review_candidate_only": True,
        "filename_or_title_evidence_is_not_import_proof": True,
        "ambiguous_nominal_evidence_requires_manual_provenance_review": True,
        "unique_nominal_evidence_requires_manual_provenance_review": True,
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
