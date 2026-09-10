#!/usr/bin/env python3
"""Read-only evidence audit for one-way provenance on failed source aliases.

A companion reference is not treated as source identity. This audit only asks
whether one-way mixed provenance can be explained by records coalescing onto an
earlier owner with the same effective (reference_type, normalized_name) identity.
Class-card packs are also marked as a distinct evidence category because the
same spell can legitimately appear in several class folders. This marker never
confirms identity by itself and never authorizes writes or canonicalization.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_failed_import_alias_reciprocal_provenance import (
    _ref_filenames,
    summarize_reciprocal_provenance,
)
from scripts.audit_manual_import_readiness import fetch_all

_CLASS_PACKS = {
    "artificiere",
    "barbaro",
    "bardo",
    "chierico",
    "druido",
    "guerriero",
    "ladro",
    "mago",
    "monaco",
    "paladino",
    "ranger",
    "stregone",
    "warlock",
}


def _identity(record: dict[str, Any]) -> tuple[str, str]:
    return (
        str(record.get("reference_type") or "").strip().casefold(),
        str(record.get("normalized_name") or "").strip().casefold(),
    )


def _class_pack(filename: str) -> str | None:
    stem = Path(str(filename or "")).stem.casefold()
    first = re.split(r"[^a-zà-öø-ÿ]+", stem, maxsplit=1)[0]
    return first if first in _CLASS_PACKS else None


def summarize_unidirectional_identity_evidence(
    jobs: list[dict], sources: list[dict], records: list[dict]
) -> dict[str, Any]:
    reciprocal = summarize_reciprocal_provenance(jobs, sources, records)
    results: list[dict[str, Any]] = []

    for candidate in reciprocal["candidates"]:
        owner = candidate["job_filename"]
        owner_records = [r for r in records if str(r.get("source_key") or "").strip() == owner]
        for companion in candidate["companions"]:
            if companion["has_reciprocal_provenance"]:
                continue
            filename = companion["filename"]
            mixed = [r for r in owner_records if filename in _ref_filenames(r.get("source_refs"))]
            companion_owned = [r for r in records if str(r.get("source_key") or "").strip() == filename]
            companion_identities = {_identity(r) for r in companion_owned if all(_identity(r))}
            same_identity_owned = sum(
                1 for r in mixed if all(_identity(r)) and _identity(r) in companion_identities
            )
            owner_class = _class_pack(owner)
            companion_class = _class_pack(filename)
            shared_class_card_candidate = bool(
                owner_class and companion_class and owner_class != companion_class
            )
            results.append(
                {
                    "job_filename": owner,
                    "companion_filename": filename,
                    "mixed_records": len(mixed),
                    "companion_owned_records": len(companion_owned),
                    "mixed_records_with_companion_owned_same_identity": same_identity_owned,
                    "mixed_records_without_companion_owned_same_identity": len(mixed) - same_identity_owned,
                    "one_way_provenance": True,
                    "shared_class_card_candidate": shared_class_card_candidate,
                    "owner_class_pack": owner_class,
                    "companion_class_pack": companion_class,
                    "identity_confirmed": False,
                    "requires_manual_reconciliation": True,
                }
            )

    shared_candidates = sum(1 for row in results if row["shared_class_card_candidate"])
    return {
        "unidirectional_pairs": sorted(results, key=lambda r: (r["job_filename"], r["companion_filename"])),
        "shared_class_card_candidate_pairs": shared_candidates,
        "shared_class_card_candidate_is_confirmation": False,
        "one_way_provenance_confirms_identity": False,
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
    print(json.dumps(summarize_unidirectional_identity_evidence(jobs, sources, records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Unidirectional identity audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
