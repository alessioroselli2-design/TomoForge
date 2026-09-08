#!/usr/bin/env python3
"""Read-only audit of structured historical artifacts for zero-import vision sources.

Checked-in analysis artifacts are diagnostic provenance evidence only. A filename,
page-count, or extracted-text match never authorizes import, OCR, external
processing, database writes, review-state changes, retries, or canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all


def _artifact_key(value: Any) -> str:
    filename = Path(str(value or "").strip()).name.casefold()
    if filename.endswith(".pdf"):
        filename = filename[:-4]
    filename = re.sub(r"[_\-\s]*\d{13}$", "", filename)
    return re.sub(r"[^a-z0-9]+", "", filename)


def _load_json_list(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path.name} must contain a JSON list")
    return [item for item in payload if isinstance(item, dict)]


def summarize_zero_import_structured_artifacts(
    sources: list[dict], analyses: list[dict]
) -> dict[str, Any]:
    analyses_by_key: dict[str, list[dict]] = {}
    for analysis in analyses:
        key = _artifact_key(analysis.get("filename"))
        if key:
            analyses_by_key.setdefault(key, []).append(analysis)

    blocked_ids: list[str] = []
    exact_ids: list[str] = []
    filename_only_ids: list[str] = []
    ambiguous_ids: list[str] = []
    no_artifact_ids: list[str] = []
    text_present_ids: list[str] = []
    zero_text_ids: list[str] = []

    for source in sources:
        if str(source.get("source_status") or "") != "active":
            continue
        if str(source.get("import_state") or "") != "catalogued":
            continue
        if str(source.get("text_mode") or "") not in {"vision_required", "mixed"}:
            continue
        if source.get("imported_record_count") not in (None, 0):
            continue

        source_id = str(source.get("id") or "").strip()
        if not source_id:
            continue
        blocked_ids.append(source_id)

        key = _artifact_key(source.get("physical_filename"))
        matches = analyses_by_key.get(key, []) if key else []
        if len(matches) > 1:
            ambiguous_ids.append(source_id)
            continue
        if not matches:
            no_artifact_ids.append(source_id)
            continue

        analysis = matches[0]
        source_pages = int(source.get("physical_pages") or 0)
        artifact_pages = int(analysis.get("pages") or 0)
        if source_pages > 0 and artifact_pages > 0 and source_pages == artifact_pages:
            exact_ids.append(source_id)
        else:
            filename_only_ids.append(source_id)

        total_characters = int(analysis.get("total_characters") or 0)
        if total_characters > 0:
            text_present_ids.append(source_id)
        else:
            zero_text_ids.append(source_id)

    return {
        "zero_import_vision_sources_total": len(blocked_ids),
        "zero_import_sources_with_filename_and_page_count_artifact_evidence": len(exact_ids),
        "zero_import_sources_with_filename_only_artifact_evidence": len(filename_only_ids),
        "zero_import_sources_with_ambiguous_artifact_evidence": len(ambiguous_ids),
        "zero_import_sources_without_structured_artifact_evidence": len(no_artifact_ids),
        "zero_import_sources_with_historical_extracted_text": len(text_present_ids),
        "zero_import_sources_with_historical_zero_text": len(zero_text_ids),
        "source_ids_with_filename_and_page_count_artifact_evidence": sorted(exact_ids),
        "source_ids_with_filename_only_artifact_evidence": sorted(filename_only_ids),
        "source_ids_with_ambiguous_artifact_evidence": sorted(ambiguous_ids),
        "source_ids_without_structured_artifact_evidence": sorted(no_artifact_ids),
        "source_ids_with_historical_extracted_text": sorted(text_present_ids),
        "source_ids_with_historical_zero_text": sorted(zero_text_ids),
        "historical_artifact_evidence_is_diagnostic_only": True,
        "historical_extracted_text_does_not_authorize_import": True,
        "ocr_authorized": False,
        "external_processing_authorized": False,
        "automatic_import_authorized": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "review_state_mutation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    sources = await fetch_all(db.private_reference_sources)
    analyses = _load_json_list(REPO_DIR / ".agents" / "outputs" / "spell-pdf-analysis.json")
    print(
        json.dumps(
            summarize_zero_import_structured_artifacts(sources, analyses),
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Zero-import structured artifact audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
