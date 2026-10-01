#!/usr/bin/env python3
"""Audit and, when explicitly authorized, verify pending MPMM monsters.

The command takes one immutable snapshot of the pending MPMM backlog and splits
it into deterministic batches.  Every batch is OCR-audited before any row in
that batch is written.  A blocked row does not prevent independent repairable
rows from being verified, but it is always retained in the final report.

Default operation is read-only.  ``--execute`` additionally requires the exact
confirmation token and is refused unless the initial live snapshot contains
the expected 131 pending and 113 verified records.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.db import db
from scripts import repair_monsters_from_source as repair
from services.ocr_semantic_gates import OCR_REVIEW_FLAG, monster_semantic_numeric_flags

LOGICAL_SOURCE_ID = "mpmm_2022_it"
EXPECTED_PENDING = 131
EXPECTED_VERIFIED = 113
DEFAULT_BATCH_SIZE = 25
CONFIRMATION_TOKEN = "VERIFY_MPMM_PENDING_131"


def _logical_source_ids(record: dict[str, Any]) -> set[str]:
    return {
        str(ref.get("logical_source_id") or "").strip()
        for ref in (record.get("source_refs") or [])
        if isinstance(ref, dict) and ref.get("logical_source_id")
    }


def _is_mpmm(record: dict[str, Any]) -> bool:
    return (
        str(record.get("reference_type") or "") == "monster"
        and LOGICAL_SOURCE_ID in _logical_source_ids(record)
    )


def _fingerprint(records: list[dict[str, Any]]) -> str:
    payload = ",".join(sorted(str(row.get("id") or "") for row in records))
    return hashlib.sha256(payload.encode()).hexdigest()


def _partition(records: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    ordered = sorted(records, key=repair._record_sort_key)
    return [ordered[offset : offset + size] for offset in range(0, len(ordered), size)]


def _verified_proposal(report: dict[str, Any]) -> dict[str, Any]:
    after = report["after"]
    flags = {str(flag) for flag in (after.get("review_flags") or [])}
    permitted = {OCR_REVIEW_FLAG, repair.REPAIR_FLAG}
    residual = flags - permitted
    if residual:
        raise repair.RepairBlocked(
            "residual_review_flags",
            ",".join(sorted(residual)),
        )
    attributes = dict(after.get("attributes") or {})
    failures = monster_semantic_numeric_flags(attributes)
    if failures:
        raise repair.RepairBlocked("verification_gate_failure", ",".join(sorted(failures)))
    return {
        "attributes": attributes,
        "review_flags": sorted(flags - permitted),
        "review_status": "verified",
    }


async def _revalidate_pending(collection: Any, originals: list[dict[str, Any]]) -> None:
    for original in originals:
        current = await collection.find_one({"id": str(original["id"])})
        if current is None:
            raise repair.RepairBlocked("concurrent_record_missing", str(original["id"]))
        for field in ("review_status", "source_text_checksum", "canonical_id"):
            if current.get(field) != original.get(field):
                raise repair.RepairBlocked(
                    "concurrent_record_drift", f"{original['id']}:{field}"
                )
        if not _is_mpmm(current):
            raise repair.RepairBlocked("concurrent_provenance_drift", str(original["id"]))


async def _apply_verified(
    collection: Any,
    history: Any,
    original: dict[str, Any],
    proposal: dict[str, Any],
    *,
    updated_at: str,
) -> None:
    if original.get("canonical_id"):
        raise repair.RepairBlocked("canonical_record_linked")
    owner = str(original.get("user_id") or "").strip()
    if not owner:
        raise repair.RepairBlocked("missing_owner_for_review_history")
    entry = {
        "id": f"review_{uuid.uuid4().hex}",
        "reference_id": str(original["id"]),
        "user_id": owner,
        "reviewer_id": owner,
        "reviewer_name": "TomoForge source-guided MPMM audit",
        "reviewer_email": "",
        "reviewed_at": updated_at,
        "review_status": "verified",
        "review_notes": (
            "Verifica source-guided sulla fonte italiana ufficiale MPMM; "
            "identità, CA, PF/dadi, velocità e provenance concordi."
        ),
    }
    await history.insert_one(entry)
    try:
        query = {
            "id": str(original["id"]),
            "review_status": "pending",
            "source_text_checksum": str(original.get("source_text_checksum") or ""),
        }
        result = await collection.update_one(
            query,
            {"$set": {**proposal, "updated_at": updated_at}},
        )
        if result.matched_count != 1:
            raise repair.RepairBlocked("concurrent_record_drift", str(original["id"]))
    except Exception:
        await history.delete_one({"id": entry["id"], "reference_id": entry["reference_id"]})
        raise

    verified = await collection.find_one({"id": str(original["id"])})
    if verified is None or str(verified.get("review_status") or "") != "verified":
        raise RuntimeError("post-write verification status failure")
    flags = {str(flag) for flag in (verified.get("review_flags") or [])}
    if OCR_REVIEW_FLAG in flags or repair.REPAIR_FLAG in flags:
        raise RuntimeError("post-write verification flag cleanup failure")
    if verified.get("canonical_id") != original.get("canonical_id"):
        raise RuntimeError("post-write canonical link drift")
    if verified.get("source_refs") != original.get("source_refs"):
        raise RuntimeError("post-write provenance drift")
    if str(verified.get("updated_at") or "") != updated_at:
        raise RuntimeError("post-write batch timestamp drift")


async def _run(args: argparse.Namespace) -> int:
    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    if not 1 <= args.batch_size <= 25:
        raise RuntimeError("batch size must be between 1 and 25")
    if args.execute and args.confirm != CONFIRMATION_TOKEN:
        raise RuntimeError("MPMM confirmation token mismatch")

    collection = db.private_reference_records
    all_monsters = await repair._fetch_all(collection, {"reference_type": "monster"})
    mpmm = [row for row in all_monsters if _is_mpmm(row)]
    pending = [row for row in mpmm if str(row.get("review_status") or "") == "pending"]
    verified_before = [
        row for row in mpmm if str(row.get("review_status") or "") == "verified"
    ]
    if args.execute and (
        len(pending) != EXPECTED_PENDING or len(verified_before) != EXPECTED_VERIFIED
    ):
        raise RuntimeError(
            "MPMM initial-state drift: "
            f"pending={len(pending)} verified={len(verified_before)}"
        )

    active_sources = await repair._fetch_all(
        db.private_reference_sources, {"source_status": "active"}
    )
    stage_args = argparse.Namespace(
        execute=False,
        target_set="batch_mpmm_pending_131",
        pdf_root=args.pdf_root,
        allow_r2_download=args.allow_r2_download,
        dpi=args.dpi,
        languages=args.languages,
        psm=args.psm,
        comparison_psm=args.comparison_psm,
    )
    reports: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    batch_reports: list[dict[str, Any]] = []
    cache = repair.SourcePdfCache(args.pdf_root, args.allow_r2_download)
    try:
        for number, batch in enumerate(_partition(pending, args.batch_size), start=1):
            batch_ok: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
            batch_blocked: list[dict[str, Any]] = []
            for record in batch:
                try:
                    report = await repair._repair_one(
                        collection, record, active_sources, cache, stage_args
                    )
                    proposal = _verified_proposal(report)
                    batch_ok.append((record, report, proposal))
                except repair.RepairBlocked as exc:
                    item = {
                        "record_id": record.get("id"),
                        "name": record.get("name"),
                        "reason": exc.reason,
                        "detail": exc.detail,
                        "executed": False,
                        **({"diagnostics": exc.diagnostics} if exc.diagnostics else {}),
                    }
                    batch_blocked.append(item)
                except Exception as exc:
                    batch_blocked.append(
                        {
                            "record_id": record.get("id"),
                            "name": record.get("name"),
                            "reason": "crash_eccezione_raw",
                            "detail": str(exc),
                            "executed": False,
                        }
                    )

            timestamp = None
            if args.execute and batch_ok:
                await _revalidate_pending(collection, [item[0] for item in batch_ok])
                timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                for original, report, proposal in batch_ok:
                    await _apply_verified(
                        collection,
                        db.private_reference_review_history,
                        original,
                        proposal,
                        updated_at=timestamp,
                    )
                    report["after"] = {**report["after"], **proposal}
                    report["executed"] = True
            reports.extend(report for _, report, _ in batch_ok)
            blocked.extend(batch_blocked)
            batch_reports.append(
                {
                    "batch": number,
                    "target": len(batch),
                    "repairable": len(batch_ok),
                    "blocked": len(batch_blocked),
                    "updates_performed": sum(
                        1 for _, report, _ in batch_ok if report.get("executed")
                    ),
                    "batch_updated_at": timestamp,
                    "blocked_records": batch_blocked,
                }
            )
    finally:
        cache.close()

    after = await repair._fetch_all(collection, {"reference_type": "monster"})
    mpmm_after = [row for row in after if _is_mpmm(row)]
    verified_after = [
        row for row in mpmm_after if str(row.get("review_status") or "") == "verified"
    ]
    protected_verified_fingerprint = _fingerprint(verified_before)
    if args.execute:
        still_verified = [
            row
            for row in verified_after
            if str(row.get("id") or "")
            in {str(item.get("id") or "") for item in verified_before}
        ]
        if _fingerprint(still_verified) != protected_verified_fingerprint:
            raise RuntimeError("protected MPMM verified-record set drifted during execution")
    final = {
        "dry_run": not args.execute,
        "logical_source_id": LOGICAL_SOURCE_ID,
        "initial_pending": len(pending),
        "initial_verified": len(verified_before),
        "protected_verified_fingerprint_sha256": protected_verified_fingerprint,
        "target_fingerprint_sha256": _fingerprint(pending),
        "targets": len(pending),
        "repairable": len(reports),
        "blocked": len(blocked),
        "updates_performed": sum(1 for report in reports if report.get("executed")),
        "final_pending": sum(
            str(row.get("review_status") or "") == "pending" for row in mpmm_after
        ),
        "final_verified": len(verified_after),
        "global_monsters": len(after),
        "batches": batch_reports,
        "blocked_records": blocked,
        "reports": reports,
    }
    print("FINAL_REPORT")
    print(json.dumps(final, ensure_ascii=False, sort_keys=True))
    return 0 if not blocked else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process pending MPMM monsters")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--pdf-root", default="")
    parser.add_argument("--allow-r2-download", action="store_true")
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--languages", default="ita")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--comparison-psm", type=int, default=4)
    return parser


def main() -> int:
    return asyncio.run(_run(_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
