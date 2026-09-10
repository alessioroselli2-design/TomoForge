#!/usr/bin/env python3
"""Read-only authority-backed evidence audit for shared class spell cards.

This layer refines generic non-class evidence by requiring a matching structured
identity to be traceable to an active registry source whose source_role is
`authority`. Authority evidence is supporting evidence only: it does not confirm
record identity and never authorizes retry, database writes, review mutation, or
canonicalization.
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

from scripts.audit_failed_import_alias_reciprocal_provenance import _ref_filenames
from scripts.audit_manual_import_readiness import fetch_all
from scripts.audit_unidirectional_alias_identity_evidence import (
    _identity,
    summarize_unidirectional_identity_evidence,
)


def summarize_authority_backed_shared_spell_evidence(
    jobs: list[dict], sources: list[dict], records: list[dict]
) -> dict[str, Any]:
    base = summarize_unidirectional_identity_evidence(jobs, sources, records)

    authority_filenames = {
        str(source.get("physical_filename") or "").strip()
        for source in sources
        if str(source.get("source_role") or "").strip().casefold() == "authority"
        and str(source.get("source_status") or "").strip().casefold() == "active"
        and str(source.get("physical_filename") or "").strip()
    }

    authority_identities = {
        _identity(record)
        for record in records
        if all(_identity(record))
        and (
            str(record.get("source_key") or "").strip() in authority_filenames
            or bool(_ref_filenames(record.get("source_refs")) & authority_filenames)
        )
    }

    rows: list[dict[str, Any]] = []
    for pair in base["unidirectional_pairs"]:
        owner = pair["job_filename"]
        companion = pair["companion_filename"]
        owner_records = [
            record
            for record in records
            if str(record.get("source_key") or "").strip() == owner
            and companion in _ref_filenames(record.get("source_refs"))
        ]
        authority_matches = sum(
            1
            for record in owner_records
            if all(_identity(record)) and _identity(record) in authority_identities
        )
        row = dict(pair)
        row["mixed_records_with_active_authority_same_identity"] = authority_matches
        row["mixed_records_without_active_authority_same_identity"] = len(owner_records) - authority_matches
        row["active_authority_same_identity_is_supporting_evidence"] = authority_matches > 0
        rows.append(row)

    shared_rows = [row for row in rows if row["shared_class_card_candidate"]]
    shared_with_authority = sum(
        1 for row in shared_rows if row["active_authority_same_identity_is_supporting_evidence"]
    )

    return {
        "unidirectional_pairs": sorted(rows, key=lambda r: (r["job_filename"], r["companion_filename"])),
        "active_authority_registry_filenames": len(authority_filenames),
        "active_authority_structured_identities": len(authority_identities),
        "shared_class_card_candidate_pairs": len(shared_rows),
        "shared_class_card_candidate_pairs_with_active_authority_identity_evidence": shared_with_authority,
        "authority_identity_evidence_is_confirmation": False,
        "requires_manual_reconciliation": True,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
        "review_state_mutation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db
    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    jobs, sources, records = await asyncio.gather(
        fetch_all(db.private_manual_import_jobs),
        fetch_all(db.private_reference_sources),
        fetch_all(db.private_reference_records),
    )
    print(json.dumps(summarize_authority_backed_shared_spell_evidence(jobs, sources, records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Authority-backed shared spell audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
