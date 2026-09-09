#!/usr/bin/env python3
"""Read-only audit of deterministic parser language support for text-only aids.

This audit is deliberately narrower than a real PDF parse. It checks whether a
text-only multilingual extraction aid identified by the provenance audit uses a
language for which the current deterministic parser has explicit recognition
heuristics. It does not read PDF bytes, execute OCR, translate content, import
records, mutate review state, or authorize canonicalization.

A positive result means only "safe candidate for a later bounded native-text
parser probe". It does not prove that the specific PDF will parse correctly.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Iterable

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all
from scripts.audit_multilingual_extraction_aids import (
    summarize_multilingual_extraction_aids,
)
from scripts.audit_zero_import_registry_sha_peers import _norm

# reference_library.py contains dedicated Italian title heuristics plus explicit
# Spanish class/race/subrace/feat vocabularies. Other languages may still pass
# generic heading rules, but that is not enough to claim explicit support here.
DEFAULT_EXPLICIT_PARSER_LANGUAGES = frozenset({"it", "es"})


def summarize_multilingual_parser_support(
    sources: list[dict],
    *,
    explicit_parser_languages: Iterable[str] = DEFAULT_EXPLICIT_PARSER_LANGUAGES,
) -> dict[str, Any]:
    """Classify text-only multilingual aids by explicit parser-language support."""

    base = summarize_multilingual_extraction_aids(sources)
    supported_languages = {_norm(value) for value in explicit_parser_languages if _norm(value)}
    source_by_id = {
        str(source.get("id") or "").strip(): source
        for source in sources
        if str(source.get("id") or "").strip()
    }

    supported_pairs: list[str] = []
    unsupported_pairs: list[str] = []
    states: dict[str, str] = {}
    supported_targets: set[str] = set()
    unsupported_targets: set[str] = set()

    text_only_map = base["text_only_multilingual_extraction_aid_peer_ids_by_source"]
    for source_id, peer_ids in sorted(text_only_map.items()):
        for peer_id in peer_ids:
            peer = source_by_id.get(peer_id) or {}
            language = _norm(peer.get("language"))
            pair_id = f"{source_id}->{peer_id}"
            if language in supported_languages:
                states[pair_id] = "explicit_language_heuristics"
                supported_pairs.append(pair_id)
                supported_targets.add(source_id)
            else:
                states[pair_id] = "no_explicit_language_heuristics"
                unsupported_pairs.append(pair_id)
                unsupported_targets.add(source_id)

    difficult_with_text_only = set(
        base["zero_import_difficult_sources_with_text_only_multilingual_extraction_aid"]
    )
    return {
        "text_only_multilingual_aid_pairs_checked": len(states),
        "text_only_multilingual_aid_pairs_with_explicit_parser_language_support": len(supported_pairs),
        "text_only_multilingual_aid_pairs_without_explicit_parser_language_support": len(unsupported_pairs),
        "parser_language_support_state_by_pair": dict(sorted(states.items())),
        "text_only_multilingual_aid_pair_ids_with_explicit_parser_language_support": sorted(supported_pairs),
        "text_only_multilingual_aid_pair_ids_without_explicit_parser_language_support": sorted(unsupported_pairs),
        "zero_import_difficult_sources_with_text_only_aid_and_explicit_parser_language_support": sorted(
            difficult_with_text_only & supported_targets
        ),
        "zero_import_difficult_sources_with_text_only_aid_without_explicit_parser_language_support": sorted(
            difficult_with_text_only & unsupported_targets
        ),
        "explicit_parser_languages": sorted(supported_languages),
        "compatibility_claim_is_language_heuristics_only": True,
        "specific_pdf_parse_verified": False,
        "bounded_native_text_parser_probe_authorized": False,
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
    print(json.dumps(summarize_multilingual_parser_support(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Multilingual parser-support audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
