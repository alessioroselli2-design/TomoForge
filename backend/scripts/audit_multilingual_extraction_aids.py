#!/usr/bin/env python3
"""Read-only audit for intentional multilingual extraction-aid peers.

A source in another language may be intentionally retained when it provides
cleaner text extraction or structural guidance for the same logical manual.
This audit identifies those peers without treating them as interchangeable
content or translation proof.

No OCR, translation, external processing, import, database mutation, review
state mutation, deletion, or canonicalization is authorized by this audit.
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
from scripts.audit_zero_import_registry_sha_peers import _norm


def _eligible_extraction_aid(source: dict) -> bool:
    return (
        _norm(source.get("text_mode")) == "text"
        and _norm(source.get("source_role")) == "extraction_aid"
        and _norm(source.get("source_status")) in {"active", "superseded"}
        and _norm(source.get("import_state")) in {"catalogued", "imported"}
    )


def summarize_multilingual_extraction_aids(sources: list[dict]) -> dict[str, Any]:
    by_logical_id: dict[str, list[dict]] = defaultdict(list)
    for source in sources:
        logical_id = _norm(source.get("logical_source_id"))
        if logical_id:
            by_logical_id[logical_id].append(source)

    pair_ids: list[str] = []
    peer_map: dict[str, list[str]] = {}
    logical_ids: set[str] = set()

    for source in sources:
        source_id = str(source.get("id") or "").strip()
        logical_id = _norm(source.get("logical_source_id"))
        source_language = _norm(source.get("language"))
        if not source_id or not logical_id or not source_language:
            continue
        if _norm(source.get("source_role")) == "extraction_aid":
            continue

        peers: list[str] = []
        for peer in by_logical_id.get(logical_id, []):
            peer_id = str(peer.get("id") or "").strip()
            peer_language = _norm(peer.get("language"))
            if (
                peer_id
                and peer_id != source_id
                and peer_language
                and peer_language != source_language
                and _eligible_extraction_aid(peer)
            ):
                peers.append(peer_id)
                pair_ids.append(f"{source_id}->{peer_id}")
                logical_ids.add(logical_id)

        if peers:
            peer_map[source_id] = sorted(set(peers))

    unique_pairs = sorted(set(pair_ids))
    return {
        "multilingual_extraction_aid_pairs": len(unique_pairs),
        "logical_sources_with_multilingual_extraction_aid": len(logical_ids),
        "multilingual_extraction_aid_pair_ids": unique_pairs,
        "multilingual_extraction_aid_peer_ids_by_source": dict(sorted(peer_map.items())),
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
