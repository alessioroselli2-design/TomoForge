#!/usr/bin/env python3
"""Read-only verified-authority evidence audit for shared class spell cards.

This refinement only treats an active authority-source identity match as stronger
supporting evidence when at least one matching authority record is itself marked
`verified`. Residual pairs are classified conservatively so review can distinguish
verified authority evidence, unverified authority evidence, class-only provenance,
and ambiguous/inconsistent evidence. The result remains support-only: no record
identity is confirmed and no retry, database write, review-state mutation, or
canonicalization is authorized.
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

AUTHORITATIVE_VERIFIED = "authoritative_source_with_verified_record"
AUTHORITATIVE_UNVERIFIED = "authoritative_source_with_unverified_record"
CLASS_SOURCES_ONLY = "class_sources_only"
AMBIGUOUS_REVIEW = "ambiguous_or_inconsistent_requires_review"

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_failed_import_alias_reciprocal_provenance import _ref_filenames
from scripts.audit_manual_import_readiness import fetch_all
from scripts.audit_unidirectional_alias_identity_evidence import _identity
from scripts.audit_authority_backed_shared_spells import summarize_authority_backed_shared_spell_evidence


def _record_is_class_sources_only(record: dict[str, Any], owner: str, companion: str) -> bool:
    """Return True only when provenance is explicitly limited to the two class aliases.

    Any additional, unknown, extraction-aid, inactive/superseded authority, or other
    provenance keeps the record in manual review rather than being guessed as class-only.
    """
    refs = set(_ref_filenames(record.get("source_refs")))
    source_key = str(record.get("source_key") or "").strip()
    if source_key:
        refs.add(source_key)
    if not refs:
        return False
    return refs.issubset({owner, companion})


def summarize_verified_authority_shared_spell_evidence(
    jobs: list[dict], sources: list[dict], records: list[dict]
) -> dict[str, Any]:
    base = summarize_authority_backed_shared_spell_evidence(jobs, sources, records)

    authority_filenames = {
        str(source.get("physical_filename") or "").strip()
        for source in sources
        if str(source.get("source_role") or "").strip().casefold() == "authority"
        and str(source.get("source_status") or "").strip().casefold() == "active"
        and str(source.get("physical_filename") or "").strip()
    }

    active_authority_identities = {
        _identity(record)
        for record in records
        if all(_identity(record))
        and (
            str(record.get("source_key") or "").strip() in authority_filenames
            or bool(_ref_filenames(record.get("source_refs")) & authority_filenames)
        )
    }
    verified_authority_identities = {
        _identity(record)
        for record in records
        if str(record.get("review_status") or "").strip().casefold() == "verified"
        and all(_identity(record))
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
        active_matches = sum(
            1
            for record in owner_records
            if all(_identity(record)) and _identity(record) in active_authority_identities
        )
        verified_matches = sum(
            1
            for record in owner_records
            if all(_identity(record)) and _identity(record) in verified_authority_identities
        )
        row = dict(pair)
        row["mixed_records_with_active_authority_same_identity"] = active_matches
        row["mixed_records_with_verified_active_authority_same_identity"] = verified_matches
        row["mixed_records_without_verified_active_authority_same_identity"] = len(owner_records) - verified_matches
        row["verified_active_authority_same_identity_is_stronger_supporting_evidence"] = verified_matches > 0

        record_evidence_classes: set[str] = set()
        for record in owner_records:
            identity = _identity(record)
            if not all(identity):
                record_evidence_classes.add(AMBIGUOUS_REVIEW)
            elif identity in verified_authority_identities:
                record_evidence_classes.add(AUTHORITATIVE_VERIFIED)
            elif identity in active_authority_identities:
                record_evidence_classes.add(AUTHORITATIVE_UNVERIFIED)
            elif _record_is_class_sources_only(record, owner, companion):
                record_evidence_classes.add(CLASS_SOURCES_ONLY)
            else:
                record_evidence_classes.add(AMBIGUOUS_REVIEW)

        if len(record_evidence_classes) == 1:
            evidence_classification = next(iter(record_evidence_classes))
        else:
            evidence_classification = AMBIGUOUS_REVIEW
        row["shared_spell_evidence_classification"] = evidence_classification
        row["classification_requires_review"] = evidence_classification == AMBIGUOUS_REVIEW

        if verified_matches > 0:
            row["residual_review_reason"] = None
        elif active_matches > 0:
            row["residual_review_reason"] = "active_authority_identity_present_but_not_verified"
        else:
            row["residual_review_reason"] = "no_active_authority_same_identity"
        rows.append(row)

    shared_rows = [row for row in rows if row["shared_class_card_candidate"]]
    shared_with_verified_authority = sum(
        1
        for row in shared_rows
        if row["verified_active_authority_same_identity_is_stronger_supporting_evidence"]
    )
    residual_shared_rows = sorted(
        (
            row
            for row in shared_rows
            if not row["verified_active_authority_same_identity_is_stronger_supporting_evidence"]
        ),
        key=lambda r: (r["job_filename"], r["companion_filename"]),
    )
    residual_reason_counts = Counter(row["residual_review_reason"] for row in residual_shared_rows)
    evidence_classification_counts = Counter(
        row["shared_spell_evidence_classification"] for row in shared_rows
    )
    classification_review_rows = sorted(
        (row for row in shared_rows if row["classification_requires_review"]),
        key=lambda r: (r["job_filename"], r["companion_filename"]),
    )

    return {
        "unidirectional_pairs": sorted(rows, key=lambda r: (r["job_filename"], r["companion_filename"])),
        "active_authority_structured_identities": len(active_authority_identities),
        "verified_active_authority_structured_identities": len(verified_authority_identities),
        "shared_class_card_candidate_pairs": len(shared_rows),
        "shared_class_card_candidate_pairs_by_evidence_classification": dict(
            sorted(evidence_classification_counts.items())
        ),
        "shared_class_card_candidate_pairs_with_verified_active_authority_identity_evidence": shared_with_verified_authority,
        "shared_class_card_candidate_pairs_without_verified_active_authority_identity_evidence": len(residual_shared_rows),
        "shared_class_card_candidate_pairs_requiring_classification_review": classification_review_rows,
        "residual_shared_class_card_candidate_pairs_by_reason": dict(sorted(residual_reason_counts.items())),
        "residual_shared_class_card_candidate_pairs": residual_shared_rows,
        "verified_authority_identity_evidence_is_confirmation": False,
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
    print(json.dumps(summarize_verified_authority_shared_spell_evidence(jobs, sources, records), sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Verified-authority shared spell audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
