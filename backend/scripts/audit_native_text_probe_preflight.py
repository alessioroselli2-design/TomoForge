#!/usr/bin/env python3
"""Read-only preflight gate for a bounded native-text parser probe.

This gate deliberately stops before reading PDF bytes. It combines the existing
multilingual parser-language audit with source metadata so that a source is only
classified as a bounded native-text probe candidate when the extraction aid is
active, explicitly text-based, unimported, and uses a language with explicit
parser heuristics. It does not run OCR, translate, import, mutate review state,
or authorize canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all
from scripts.audit_multilingual_parser_support import summarize_multilingual_parser_support
from scripts.audit_zero_import_registry_sha_peers import _norm


def summarize_native_text_probe_preflight(sources: list[dict]) -> dict[str, Any]:
    support = summarize_multilingual_parser_support(sources)
    source_by_id = {
        str(source.get("id") or "").strip(): source
        for source in sources
        if str(source.get("id") or "").strip()
    }

    ready_pairs: list[str] = []
    blocked_pairs: dict[str, list[str]] = {}

    for pair_id in support[
        "text_only_multilingual_aid_pair_ids_with_explicit_parser_language_support"
    ]:
        target_id, aid_id = pair_id.split("->", 1)
        target = source_by_id.get(target_id) or {}
        aid = source_by_id.get(aid_id) or {}
        reasons: list[str] = []

        if _norm(aid.get("source_role")) != "extraction_aid":
            reasons.append("aid_role_not_extraction_aid")
        if _norm(aid.get("source_status")) != "active":
            reasons.append("aid_not_active")
        if _norm(aid.get("text_mode")) != "text":
            reasons.append("aid_not_native_text")
        if int(aid.get("imported_record_count") or 0) != 0:
            reasons.append("aid_already_has_imported_records")
        if _norm(target.get("source_status")) not in {"active", "superseded"}:
            reasons.append("target_not_operational")
        if int(target.get("imported_record_count") or 0) != 0:
            reasons.append("target_already_has_imported_records")
        if _norm(target.get("ruleset")) != _norm(aid.get("ruleset")):
            reasons.append("ruleset_mismatch")

        if reasons:
            blocked_pairs[pair_id] = reasons
        else:
            ready_pairs.append(pair_id)

    return {
        "native_text_probe_preflight_pairs_checked": len(ready_pairs) + len(blocked_pairs),
        "native_text_probe_preflight_ready_pairs": sorted(ready_pairs),
        "native_text_probe_preflight_ready_count": len(ready_pairs),
        "native_text_probe_preflight_blocked_pairs": dict(sorted(blocked_pairs.items())),
        "native_text_probe_preflight_blocked_count": len(blocked_pairs),
        "preflight_reads_pdf_bytes": False,
        "specific_pdf_parse_verified": False,
        "bounded_native_text_parser_probe_executed": False,
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
    print(json.dumps(summarize_native_text_probe_preflight(sources), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Native-text probe preflight audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
