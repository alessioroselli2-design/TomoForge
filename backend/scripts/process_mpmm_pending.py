#!/usr/bin/env python3
"""Audit and, when explicitly authorized, verify pending MPMM monsters.

The command takes one immutable snapshot of the pending MPMM backlog and splits
it into deterministic batches.  Every batch is OCR-audited before any row in
that batch is written.  A blocked row does not prevent independent repairable
rows from being verified, but it is always retained in the final report.

Default operation is read-only.  ``--execute`` additionally requires the exact
confirmation token and is refused unless the initial live snapshot contains
the expected 17 pending MPMM records, 178 verified MPMM records, and 227 verified monsters globally..
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
EXPECTED_PENDING = 2
EXPECTED_MPMM_VERIFIED = 193
EXPECTED_GLOBAL_VERIFIED = 242
EXPECTED_PENDING_FINGERPRINT = "349c191cf4ab957a6628ba1bb9f2d783cfebee8cb9bb03594cd5f7fcdecb18a2"
EXPECTED_VERIFIED_FINGERPRINT = "cf9848d557804dbecca946a51377ba951ebc317ade4a165f21973f54ffbb8674"
DEFAULT_BATCH_SIZE = 25
CONFIRMATION_TOKEN = "VERIFY_MPMM_PENDING_2"


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


def _record_snapshot_sha256(record: dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _same_utc_timestamp(value: Any, expected: str) -> bool:
    def parse(raw_value: Any) -> datetime:
        if isinstance(raw_value, datetime):
            parsed = raw_value
        else:
            raw = str(raw_value or "").strip()
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            elif len(raw) >= 3 and raw[-3] in "+-" and raw[-2:].isdigit():
                raw += ":00"
            parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    try:
        return parse(value) == parse(expected)
    except (TypeError, ValueError):
        return False


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
        if _record_snapshot_sha256(current) != _record_snapshot_sha256(original):
            raise repair.RepairBlocked("concurrent_record_drift", str(original["id"]))
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
    review_notes: str | None = None,
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
        "review_notes": review_notes
        or (
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
    if not _same_utc_timestamp(verified.get("updated_at"), updated_at):
        raise RuntimeError("post-write batch timestamp drift")


async def _run(args: argparse.Namespace) -> int:
    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    if not 1 <= args.batch_size <= 25:
        raise RuntimeError("batch size must be between 1 and 25")
    if args.execute and args.confirm != CONFIRMATION_TOKEN:
        raise RuntimeError("MPMM confirmation token mismatch")

    if args.execute and args.audit_record_id:
        raise RuntimeError("focused audits are read-only")
    if args.execute_record_id and not args.execute:
        raise RuntimeError("execute-record-id requires --execute")
    if args.audit_record_id and args.execute_record_id:
        raise RuntimeError("audit-record-id and execute-record-id are mutually exclusive")
    collection = db.private_reference_records
    all_monsters = await repair._fetch_all(collection, {"reference_type": "monster"})
    mpmm = [row for row in all_monsters if _is_mpmm(row)]
    pending = [row for row in mpmm if str(row.get("review_status") or "") == "pending"]
    targets = pending
    if args.audit_record_id:
        targets = [row for row in pending if row.get("id") == args.audit_record_id]
        if len(targets) != 1:
            raise RuntimeError("focused audit requires exactly one pending MPMM record")
    elif args.execute_record_id:
        targets = [row for row in pending if row.get("id") == args.execute_record_id]
        if len(targets) != 1:
            raise RuntimeError("single-record execution requires exactly one pending MPMM record")
    verified_before = [
        row for row in mpmm if str(row.get("review_status") or "") == "verified"
    ]
    global_verified_before = [
        row for row in all_monsters if str(row.get("review_status") or "") == "verified"
    ]
    pending_fingerprint = _fingerprint(pending)
    verified_fingerprint = _fingerprint(verified_before)
    if args.execute and (
        len(pending) != EXPECTED_PENDING
        or len(verified_before) != EXPECTED_MPMM_VERIFIED
        or len(global_verified_before) != EXPECTED_GLOBAL_VERIFIED
        or pending_fingerprint != EXPECTED_PENDING_FINGERPRINT
        or verified_fingerprint != EXPECTED_VERIFIED_FINGERPRINT
    ):
        raise RuntimeError(
            "MPMM initial-state drift: "
            f"pending={len(pending)} "
            f"mpmm_verified={len(verified_before)} "
            f"global_verified={len(global_verified_before)} "
            f"pending_fingerprint={pending_fingerprint} "
            f"verified_fingerprint={verified_fingerprint}"
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
        for number, batch in enumerate(_partition(targets, args.batch_size), start=1):
            batch_ok: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
            batch_blocked: list[dict[str, Any]] = []
            for record in batch:
                snapshot_sha256 = _record_snapshot_sha256(record)
                try:
                    report = await repair._repair_one(
                        collection, record, active_sources, cache, stage_args
                    )
                    report["record_snapshot_sha256"] = snapshot_sha256
                    proposal = _verified_proposal(report)
                    batch_ok.append((record, report, proposal))
                except repair.RepairBlocked as exc:
                    item = {
                        "record_snapshot_sha256": snapshot_sha256,
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
                            "record_snapshot_sha256": snapshot_sha256,
                            "record_id": record.get("id"),
                            "name": record.get("name"),
                            "reason": "crash_eccezione_raw",
                            "detail": str(exc),
                            "executed": False,
                        }
                    )

            timestamp = None
            if args.execute and batch_ok:
                timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                for original, report, proposal in batch_ok:
                    try:
                        await _revalidate_pending(collection, [original])
                        await _apply_verified(
                            collection,
                            db.private_reference_review_history,
                            original,
                            proposal,
                            updated_at=timestamp,
                            review_notes=(
                                "Verifica source-reviewed status-only: identità "
                                "confermata sulla pagina italiana registrata MPMM; "
                                "core preesistenti invariati e cross-checkati sul "
                                "corrispondente stat block MPMM inglese; nessuna "
                                "correzione numerica applicata."
                                if report.get("source_reviewed_status_only") is True
                                else None
                            ),
                        )
                    except Exception as exc:
                        current = await collection.find_one({"id": str(original["id"])})
                        flags = {
                            str(flag)
                            for flag in ((current or {}).get("review_flags") or [])
                        }
                        write_landed_cleanly = bool(
                            current is not None
                            and str(current.get("review_status") or "") == "verified"
                            and OCR_REVIEW_FLAG not in flags
                            and repair.REPAIR_FLAG not in flags
                            and current.get("canonical_id") == original.get("canonical_id")
                            and current.get("source_refs") == original.get("source_refs")
                            and _same_utc_timestamp(
                                current.get("updated_at"), timestamp
                            )
                        )
                        if not write_landed_cleanly:
                            batch_blocked.append(
                                {
                                    "record_snapshot_sha256": report.get(
                                        "record_snapshot_sha256"
                                    ),
                                    "record_id": original.get("id"),
                                    "name": original.get("name"),
                                    "reason": "write_apply_failed",
                                    "detail": str(exc),
                                    "executed": False,
                                }
                            )
                            continue
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
    protected_verified_fingerprint = verified_fingerprint
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
        "initial_global_verified": len(global_verified_before),
        "protected_verified_fingerprint_sha256": protected_verified_fingerprint,
        "target_fingerprint_sha256": (
            pending_fingerprint
            if not (args.audit_record_id or args.execute_record_id)
            else _fingerprint(targets)
        ),
        "targets": len(targets),
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
    parser.add_argument("--audit-record-id", default="", help="Read-only pending MPMM pilot")
    parser.add_argument(
        "--execute-record-id",
        default="",
        help="Execute exactly one pending MPMM record after sealed-snapshot checks",
    )
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
