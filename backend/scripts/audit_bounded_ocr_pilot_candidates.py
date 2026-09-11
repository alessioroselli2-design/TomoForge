#!/usr/bin/env python3
"""Read-only selector for bounded OCR/vision pilot candidates.

This audit ranks only registry sources whose provenance is sufficiently clear for a
small, separately authorized OCR/vision pilot. It never runs OCR, retries imports,
writes Supabase, mutates review state, or authorizes canonicalization.
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
from scripts.evaluate_text_extraction_quality import (
    EMPTY_TEXT,
    TEXT_USABLE,
    VISION_REVIEW_REQUIRED,
)

READY = "READY_FOR_BOUNDED_OCR_PILOT"
PROVENANCE_REVIEW = "NEEDS_PROVENANCE_REVIEW"
STRUCTURED = "HAS_EXISTING_STRUCTURED_EVIDENCE"
NOT_ELIGIBLE = "NOT_ELIGIBLE"

PREFLIGHT_REQUIRED = "PREFLIGHT_REQUIRED"
NATIVE_TEXT_REVIEW = "NATIVE_TEXT_PARSER_REVIEW"
VISION_PILOT_REVIEW = "VISION_OCR_PILOT_REVIEW"


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _activity(job: dict[str, Any]) -> int:
    return sum(int(job.get(field) or 0) for field in (
        "records_imported", "records_updated", "records_flagged", "records_skipped"
    ))


def _text_preflight_path(result: dict[str, Any] | None) -> str:
    """Return the next review path implied by optional text-quality evidence."""
    if not result:
        return PREFLIGHT_REQUIRED
    classification = str(result.get("classification") or "").strip()
    if classification == TEXT_USABLE:
        return NATIVE_TEXT_REVIEW
    if classification in {VISION_REVIEW_REQUIRED, EMPTY_TEXT}:
        return VISION_PILOT_REVIEW
    return PREFLIGHT_REQUIRED


def summarize_bounded_ocr_pilot_candidates(
    sources: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    text_quality_by_source_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sources_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sources_by_logical: dict[str, list[dict[str, Any]]] = defaultdict(list)
    jobs_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    text_quality_by_source_id = text_quality_by_source_id or {}

    for source in sources:
        sha = _norm(source.get("physical_sha256"))
        logical = _norm(source.get("logical_source_id"))
        if sha:
            sources_by_sha[sha].append(source)
        if logical:
            sources_by_logical[logical].append(source)
    for job in jobs:
        sha = _norm(job.get("source_fingerprint"))
        if sha:
            jobs_by_sha[sha].append(job)

    rows: list[dict[str, Any]] = []
    for source in sources:
        source_id = str(source.get("id") or "").strip()
        sha = _norm(source.get("physical_sha256"))
        logical = _norm(source.get("logical_source_id"))
        role = _norm(source.get("source_role"))
        status = _norm(source.get("source_status"))
        import_state = _norm(source.get("import_state"))
        text_mode = _norm(source.get("text_mode"))
        imported = int(source.get("imported_record_count") or 0)
        matching_jobs = jobs_by_sha.get(sha, []) if sha else []
        job_activity = sum(_activity(job) for job in matching_jobs)
        failed_jobs = sum(_norm(job.get("status")) == "failed" for job in matching_jobs)
        sha_logical_ids = {
            _norm(item.get("logical_source_id")) for item in sources_by_sha.get(sha, [])
            if _norm(item.get("logical_source_id"))
        } if sha else set()
        logical_peers = sources_by_logical.get(logical, []) if logical else []
        extraction_peers = sum(
            _norm(peer.get("source_role")) in {"extraction_aid", "visual_aid", "ingest_copy"}
            for peer in logical_peers if peer is not source
        )

        eligible_shape = (
            status == "active"
            and import_state == "catalogued"
            and text_mode in {"vision_required", "mixed"}
        )
        if not eligible_shape:
            classification = NOT_ELIGIBLE
            reason = "registry_state_not_eligible"
        elif imported > 0 or job_activity > 0:
            classification = STRUCTURED
            reason = "structured_record_evidence_exists"
        elif (
            not source_id or not sha or not logical
            or len(sha_logical_ids) != 1
            or role not in {"authority", "visual_authority"}
            or failed_jobs > 0
        ):
            classification = PROVENANCE_REVIEW
            reason = "provenance_or_prior_failure_requires_review"
        else:
            classification = READY
            reason = "clear_unique_authority_provenance_no_structured_activity"

        pages = source.get("physical_pages")
        page_count = int(pages) if pages not in (None, "") else None
        preflight = text_quality_by_source_id.get(source_id)
        rows.append({
            "source_id": source_id,
            "physical_filename": source.get("physical_filename"),
            "logical_source_id": source.get("logical_source_id"),
            "language": source.get("language"),
            "ruleset": source.get("ruleset"),
            "source_role": source.get("source_role"),
            "text_mode": source.get("text_mode"),
            "physical_pages": page_count,
            "matching_import_jobs": len(matching_jobs),
            "failed_matching_import_jobs": failed_jobs,
            "matching_job_record_activity": job_activity,
            "same_logical_source_helper_peers": extraction_peers,
            "same_sha_logical_source_count": len(sha_logical_ids),
            "classification": classification,
            "classification_reason": reason,
            "text_quality_preflight_classification": (
                preflight.get("classification") if preflight else None
            ),
            "recommended_review_path": (
                _text_preflight_path(preflight) if classification == READY else None
            ),
            "requires_manual_review": classification != READY,
        })

    priority = {READY: 0, PROVENANCE_REVIEW: 1, STRUCTURED: 2, NOT_ELIGIBLE: 3}
    rows.sort(key=lambda row: (
        priority[row["classification"]],
        row["physical_pages"] is None,
        row["physical_pages"] or 10**9,
        str(row["physical_filename"] or "").casefold(),
    ))
    counts = {name: sum(row["classification"] == name for row in rows) for name in priority}
    ready = [row for row in rows if row["classification"] == READY]
    recommended = ready[0] if ready else None
    return {
        "classification_counts": counts,
        "ready_candidates_ranked": ready,
        "all_sources": rows,
        "recommended_pilot_source_id": recommended["source_id"] if recommended else None,
        "recommended_next_step": recommended["recommended_review_path"] if recommended else None,
        "recommendation_is_execution_authorization": False,
        "text_quality_preflight_is_required_before_parser_or_vision_execution": True,
        "ocr_authorized": False,
        "translation_authorized": False,
        "external_paid_api_authorized": False,
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
    sources, jobs = await asyncio.gather(
        fetch_all(db.private_reference_sources),
        fetch_all(db.private_manual_import_jobs),
    )
    print(json.dumps(summarize_bounded_ocr_pilot_candidates(sources, jobs), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Bounded OCR pilot audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
