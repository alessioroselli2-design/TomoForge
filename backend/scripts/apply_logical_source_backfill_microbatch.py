#!/usr/bin/env python3
"""Apply a tiny, explicitly authorized logical-source provenance backfill batch.

This is deliberately separate from the read-only global approval manifest.  A write
requires a second, batch-specific authorization document that names every candidate,
pins the current global candidate fingerprint, and caps the batch at one record.
The script reconstructs the live deterministic plan immediately before writing and
rechecks every requested candidate.  It only changes ``source_refs``; review state,
AI-review metadata, canonical_id, record content and checksums are never written.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_APPROVAL_PATH = BACKEND_DIR / "provenance_backfill_approval.json"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_logical_source_coverage import fetch_all  # noqa: E402
from scripts.build_logical_source_backfill_dry_run import build_backfill_plan  # noqa: E402
from scripts.validate_logical_source_backfill_plan import (  # noqa: E402
    candidate_fingerprint,
    validate_approval_manifest,
)

MAX_MICROBATCH_WRITES = 1


def validate_batch_authorization(
    authorization: dict[str, Any],
    fresh_plan: dict[str, Any],
    global_candidate_sha256: str,
) -> tuple[list[str], list[dict[str, str]]]:
    """Validate an exact, bounded write authorization against the fresh plan."""
    errors: list[str] = []
    if authorization.get("schema_version") != 1:
        errors.append("batch authorization schema_version is unsupported")
    if authorization.get("scope") != "logical_source_provenance_microbatch":
        errors.append("batch authorization scope is invalid")
    if authorization.get("approval_state") != "microbatch_write":
        errors.append("batch authorization is not microbatch_write")
    if authorization.get("writes_authorized") is not True:
        errors.append("batch authorization does not authorize writes")
    if authorization.get("candidate_sha256") != global_candidate_sha256:
        errors.append("batch authorization candidate fingerprint is stale")

    candidates = authorization.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
        errors.append("batch authorization candidates are malformed")

    if not 1 <= len(candidates) <= MAX_MICROBATCH_WRITES:
        errors.append(f"batch must contain between 1 and {MAX_MICROBATCH_WRITES} candidates")

    normalized: list[dict[str, str]] = []
    for row in candidates:
        if not isinstance(row, dict):
            errors.append("batch candidate is malformed")
            continue
        record_id = row.get("record_id")
        logical_source_id = row.get("logical_source_id")
        if not isinstance(record_id, str) or not record_id.strip():
            errors.append("batch candidate record_id is invalid")
            continue
        if not isinstance(logical_source_id, str) or not logical_source_id.strip():
            errors.append("batch candidate logical_source_id is invalid")
            continue
        normalized.append(
            {"record_id": record_id.strip(), "logical_source_id": logical_source_id.strip()}
        )

    ids = [row["record_id"] for row in normalized]
    if len(ids) != len(set(ids)):
        errors.append("batch contains duplicate record ids")

    fresh_candidates = {
        (row["record_id"], row["logical_source_id"])
        for row in fresh_plan.get("candidates", [])
        if isinstance(row, dict)
    }
    for row in normalized:
        pair = (row["record_id"], row["logical_source_id"])
        if pair not in fresh_candidates:
            errors.append(f"batch candidate is not present in fresh deterministic plan: {row['record_id']}")

    return errors, normalized


def enrich_source_refs(
    source_refs: Any,
    logical_source_id: str,
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return provenance-enriched refs while preserving all existing ref fields."""
    if not isinstance(source_refs, list) or not source_refs:
        raise ValueError("record has no source_refs to enrich")

    enriched: list[dict[str, Any]] = []
    for raw_ref in source_refs:
        if not isinstance(raw_ref, dict):
            raise ValueError("record contains malformed source_ref")
        ref = dict(raw_ref)
        existing = ref.get("logical_source_id")
        if existing not in (None, "", logical_source_id):
            raise ValueError("record already contains incompatible logical_source_id")
        ref["logical_source_id"] = logical_source_id
        for ref_key, source_key in (
            ("source_title", "title"),
            ("ruleset", "ruleset"),
            ("authority_class", "authority_class"),
            ("source_role", "source_role"),
            ("source_status", "source_status"),
        ):
            value = source.get(source_key)
            if value is not None and ref.get(ref_key) in (None, ""):
                ref[ref_key] = value
        enriched.append(ref)
    return enriched


async def apply_microbatch(
    db: Any,
    authorization: dict[str, Any],
    global_approval: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild live plan, validate both gates, write source_refs only, then verify."""
    records, sources = await asyncio.gather(
        fetch_all(db.private_reference_records),
        fetch_all(db.private_reference_sources),
    )
    fresh_plan = build_backfill_plan(records, sources)
    fresh_sha256 = candidate_fingerprint(fresh_plan["candidates"])

    errors = validate_approval_manifest(global_approval, fresh_plan, fresh_sha256)
    batch_errors, candidates = validate_batch_authorization(
        authorization, fresh_plan, fresh_sha256
    )
    errors.extend(batch_errors)
    if errors:
        return {"mode": "microbatch_apply", "writes_performed": 0, "valid": False, "errors": errors}

    records_by_id = {row.get("id"): row for row in records if isinstance(row, dict)}
    sources_by_id = {
        row.get("logical_source_id"): row
        for row in sources
        if isinstance(row, dict) and row.get("logical_source_id")
    }

    prepared: list[tuple[str, list[dict[str, Any]]]] = []
    for candidate in candidates:
        record_id = candidate["record_id"]
        logical_source_id = candidate["logical_source_id"]
        record = records_by_id.get(record_id)
        source = sources_by_id.get(logical_source_id)
        if record is None:
            errors.append(f"live record disappeared before write: {record_id}")
            continue
        if source is None:
            errors.append(f"catalog source disappeared before write: {logical_source_id}")
            continue
        try:
            new_refs = enrich_source_refs(record.get("source_refs"), logical_source_id, source)
        except ValueError as exc:
            errors.append(f"{record_id}: {exc}")
            continue
        prepared.append((record_id, new_refs))

    if errors or len(prepared) != len(candidates):
        return {"mode": "microbatch_apply", "writes_performed": 0, "valid": False, "errors": errors}

    writes = 0
    for record_id, new_refs in prepared:
        result = await db.private_reference_records.update_one(
            {"id": record_id}, {"$set": {"source_refs": new_refs}}
        )
        if result.matched_count != 1:
            raise RuntimeError(f"expected exactly one record update for {record_id}")
        writes += 1

    verification_errors: list[str] = []
    for candidate in candidates:
        row = await db.private_reference_records.find_one({"id": candidate["record_id"]})
        refs = row.get("source_refs") if isinstance(row, dict) else None
        if not isinstance(refs, list) or not refs:
            verification_errors.append(f"post-write source_refs missing: {candidate['record_id']}")
            continue
        if any(
            not isinstance(ref, dict)
            or ref.get("logical_source_id") != candidate["logical_source_id"]
            for ref in refs
        ):
            verification_errors.append(f"post-write provenance mismatch: {candidate['record_id']}")

    return {
        "mode": "microbatch_apply",
        "writes_performed": writes,
        "valid": not verification_errors,
        "errors": verification_errors,
        "record_ids": [row["record_id"] for row in candidates],
        "candidate_sha256": fresh_sha256,
    }


async def _run(batch_path: Path, approval_path: Path) -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    authorization = json.loads(batch_path.read_text(encoding="utf-8"))
    global_approval = json.loads(approval_path.read_text(encoding="utf-8"))
    if not isinstance(authorization, dict) or not isinstance(global_approval, dict):
        raise ValueError("authorization documents must be JSON objects")

    result = await apply_microbatch(db, authorization, global_approval)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["valid"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply an explicitly authorized provenance microbatch")
    parser.add_argument("--batch", type=Path, required=True, help="Batch-specific write authorization JSON")
    parser.add_argument(
        "--approval", type=Path, default=DEFAULT_APPROVAL_PATH, help="Global preflight approval manifest"
    )
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args.batch, args.approval))
    except Exception as exc:
        print(f"Logical-source microbatch apply failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
