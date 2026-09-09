#!/usr/bin/env python3
"""Read-only audit for intentional multilingual extraction-aid peers.

A source in another language may be intentionally retained when it provides
cleaner text extraction or structural guidance for the same logical manual.
This audit identifies those peers without treating them as interchangeable
content or translation proof.

Peers normally share the same logical_source_id. A second, deliberately narrow
path also recognizes IDs shaped as ``<family>_<year>_<language>`` (for example
``phb_2014_it`` and ``phb_2014_es``), but only when each ID suffix agrees with
the source language and both sources declare the same ruleset. This avoids
using titles or filenames as identity evidence.

No OCR, translation, external processing, import, database mutation, review
state mutation, deletion, or canonicalization is authorized by this audit.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all
from scripts.audit_zero_import_registry_sha_peers import _norm

_LANGUAGE_SUFFIXED_LOGICAL_ID = re.compile(
    r"^(?P<family>.+_(?:19|20)\d{2})_(?P<language>[a-z]{2,3})$"
)


def _eligible_extraction_aid(source: dict) -> bool:
    return (
        _norm(source.get("text_mode")) == "text"
        and _norm(source.get("source_role")) == "extraction_aid"
        and _norm(source.get("source_status")) in {"active", "superseded"}
        and _norm(source.get("import_state")) in {"catalogued", "imported"}
    )


def _zero_import_difficult_source(source: dict) -> bool:
    return (
        _norm(source.get("text_mode")) in {"vision_required", "mixed"}
        and _norm(source.get("source_status")) in {"active", "superseded"}
        and _norm(source.get("import_state")) == "catalogued"
        and int(source.get("imported_record_count") or 0) == 0
        and _norm(source.get("source_role")) != "extraction_aid"
    )


def _language_suffixed_family(source: dict) -> str | None:
    """Return a conservative cross-language family key, or None.

    The logical ID must end in a 2-3 letter language suffix that exactly agrees
    with the row's language metadata. The year remains part of the family, so
    different editions cannot be paired through this fallback.
    """

    logical_id = _norm(source.get("logical_source_id"))
    language = _norm(source.get("language"))
    if not logical_id or not language:
        return None
    match = _LANGUAGE_SUFFIXED_LOGICAL_ID.fullmatch(logical_id)
    if not match or match.group("language") != language:
        return None
    return match.group("family")


def _peer_match(source: dict, peer: dict) -> tuple[str, str] | None:
    """Return (match_type, identity_key) for a verified structural peer link."""

    source_logical_id = _norm(source.get("logical_source_id"))
    peer_logical_id = _norm(peer.get("logical_source_id"))
    if source_logical_id and source_logical_id == peer_logical_id:
        return ("exact_logical_source_id", source_logical_id)

    source_family = _language_suffixed_family(source)
    peer_family = _language_suffixed_family(peer)
    source_ruleset = _norm(source.get("ruleset"))
    peer_ruleset = _norm(peer.get("ruleset"))
    if (
        source_family
        and source_family == peer_family
        and source_ruleset
        and source_ruleset == peer_ruleset
    ):
        return ("language_suffixed_family", source_family)
    return None


def summarize_multilingual_extraction_aids(sources: list[dict]) -> dict[str, Any]:
    by_logical_id: dict[str, list[dict]] = defaultdict(list)
    by_language_family: dict[str, list[dict]] = defaultdict(list)
    for source in sources:
        logical_id = _norm(source.get("logical_source_id"))
        if logical_id:
            by_logical_id[logical_id].append(source)
        family = _language_suffixed_family(source)
        if family:
            by_language_family[family].append(source)

    pair_ids: list[str] = []
    peer_map: dict[str, list[str]] = {}
    pair_match_types: dict[str, str] = {}
    identity_keys: set[str] = set()
    zero_import_targets_with_aid: list[str] = []
    zero_import_targets_without_aid: list[str] = []

    for source in sources:
        source_id = str(source.get("id") or "").strip()
        logical_id = _norm(source.get("logical_source_id"))
        source_language = _norm(source.get("language"))
        if not source_id or not logical_id or not source_language:
            continue
        if _norm(source.get("source_role")) == "extraction_aid":
            continue

        candidates: list[dict] = list(by_logical_id.get(logical_id, []))
        family = _language_suffixed_family(source)
        if family:
            candidates.extend(by_language_family.get(family, []))

        peers: list[str] = []
        seen_candidates: set[str] = set()
        for peer in candidates:
            peer_id = str(peer.get("id") or "").strip()
            if not peer_id or peer_id in seen_candidates:
                continue
            seen_candidates.add(peer_id)
            peer_language = _norm(peer.get("language"))
            match = _peer_match(source, peer)
            if (
                peer_id != source_id
                and peer_language
                and peer_language != source_language
                and _eligible_extraction_aid(peer)
                and match is not None
            ):
                match_type, identity_key = match
                pair_id = f"{source_id}->{peer_id}"
                peers.append(peer_id)
                pair_ids.append(pair_id)
                pair_match_types[pair_id] = match_type
                identity_keys.add(identity_key)

        if peers:
            peer_map[source_id] = sorted(set(peers))

        if _zero_import_difficult_source(source):
            if peers:
                zero_import_targets_with_aid.append(source_id)
            else:
                zero_import_targets_without_aid.append(source_id)

    unique_pairs = sorted(set(pair_ids))
    return {
        "multilingual_extraction_aid_pairs": len(unique_pairs),
        "logical_sources_with_multilingual_extraction_aid": len(identity_keys),
        "multilingual_extraction_aid_pair_ids": unique_pairs,
        "multilingual_extraction_aid_pair_match_types": dict(
            sorted(pair_match_types.items())
        ),
        "multilingual_extraction_aid_peer_ids_by_source": dict(sorted(peer_map.items())),
        "zero_import_difficult_sources_with_multilingual_extraction_aid": sorted(
            set(zero_import_targets_with_aid)
        ),
        "zero_import_difficult_sources_without_multilingual_extraction_aid": sorted(
            set(zero_import_targets_without_aid)
        ),
        "language_suffixed_family_requires_matching_language_metadata": True,
        "language_suffixed_family_requires_same_ruleset": True,
        "title_or_filename_matching_used": False,
        "cross_language_peer_is_intentional_extraction_evidence_only": True,
        "cross_language_peer_does_not_prove_translation_equivalence": True,
        "cross_language_peer_does_not_replace_authoritative_language_source": True,
        "duplicate_deletion_authorized": False,
        "ocr_authorized": False,
        "translation_authorized": False,
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
    print(json.dumps(summarize_multilingual_extraction_aids(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Multilingual extraction-aid audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
