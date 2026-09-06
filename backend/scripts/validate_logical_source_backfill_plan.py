#!/usr/bin/env python3
"""Validate a saved logical-source backfill dry-run against current live inputs.

This is a read-only preflight gate. It never applies backfills. A saved plan is
accepted only when it is still exactly reproducible from the current records and
source registry and still satisfies the dry-run safety contract.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_logical_source_coverage import fetch_all  # noqa: E402
from scripts.build_logical_source_backfill_dry_run import build_backfill_plan  # noqa: E402


def candidate_fingerprint(candidates: list[dict[str, str]]) -> str:
    """Return a stable SHA-256 for the exact ordered candidate set."""
    payload = json.dumps(candidates, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_backfill_plan(
    saved_plan: dict[str, Any], records: list[dict], sources: list[dict]
) -> dict[str, Any]:
    """Validate that a saved dry-run is unchanged and safe to consider further."""
    errors: list[str] = []

    if saved_plan.get("mode") != "dry_run":
        errors.append("saved plan is not dry_run")
    if saved_plan.get("writes_performed") != 0:
        errors.append("saved plan reports writes")
    if saved_plan.get("candidate_record_ids_unique") is not True:
        errors.append("saved plan does not assert unique candidate record ids")

    saved_candidates = saved_plan.get("candidates")
    if not isinstance(saved_candidates, list):
        saved_candidates = []
        errors.append("saved plan candidates are malformed")

    fresh_plan = build_backfill_plan(records, sources)
    fresh_candidates = fresh_plan["candidates"]

    if saved_candidates != fresh_candidates:
        errors.append("saved candidate set is stale or differs from current live inputs")

    count = saved_plan.get("proposed_backfills")
    if count != len(saved_candidates):
        errors.append("saved proposed_backfills does not match candidate count")

    saved_ids = [row.get("record_id") for row in saved_candidates if isinstance(row, dict)]
    if len(saved_ids) != len(set(saved_ids)):
        errors.append("saved plan contains duplicate candidate record ids")

    return {
        "mode": "preflight_read_only",
        "writes_performed": 0,
        "valid": not errors,
        "errors": errors,
        "saved_candidate_count": len(saved_candidates),
        "fresh_candidate_count": len(fresh_candidates),
        "saved_plan_sha256": candidate_fingerprint(saved_candidates),
        "fresh_plan_sha256": candidate_fingerprint(fresh_candidates),
    }


async def _run(plan_path: Path) -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    saved_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(saved_plan, dict):
        raise ValueError("Plan JSON must be an object")

    records, sources = await asyncio.gather(
        fetch_all(db.private_reference_records),
        fetch_all(db.private_reference_sources),
    )
    result = validate_backfill_plan(saved_plan, records, sources)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["valid"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only preflight for a saved logical-source backfill dry-run"
    )
    parser.add_argument("--plan", type=Path, required=True, help="Path to saved dry-run JSON")
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args.plan))
    except Exception as exc:
        print(f"Logical-source backfill preflight failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
