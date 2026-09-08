#!/usr/bin/env python3
"""Read-only audit for failed import jobs that share one Git LFS asset.

The audit inspects exact failed-job filenames under ``attached_assets`` and
compares only Git LFS pointer object IDs. A collision is diagnostic evidence of
an asset alias/copy; it never authorizes a retry, registry change, OCR, database
write, or canonicalization.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.audit_manual_import_readiness import fetch_all

_LFS_OID = re.compile(r"^oid sha256:([0-9a-f]{64})$", re.IGNORECASE)
_LFS_SIZE = re.compile(r"^size (\d+)$")


def parse_lfs_pointer(text: str) -> dict[str, Any] | None:
    """Parse a Git LFS pointer, returning its object ID and declared size."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "version https://git-lfs.github.com/spec/v1":
        return None

    oid: str | None = None
    size: int | None = None
    for line in lines[1:]:
        oid_match = _LFS_OID.match(line)
        if oid_match:
            oid = oid_match.group(1).lower()
            continue
        size_match = _LFS_SIZE.match(line)
        if size_match:
            size = int(size_match.group(1))

    if oid is None or size is None:
        return None
    return {"oid_sha256": oid, "size": size}


def _read_pointer(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        # Git LFS pointers are tiny text files. Do not read materialized PDFs.
        if path.stat().st_size > 4096:
            return None
        return parse_lfs_pointer(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


def summarize_failed_import_lfs_aliases(
    jobs: list[dict], asset_dir: Path
) -> dict[str, Any]:
    failed_jobs = [job for job in jobs if str(job.get("status") or "") == "failed"]
    by_oid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing_assets = 0
    non_pointer_assets = 0
    pointer_jobs = 0

    for job in failed_jobs:
        filename = str(job.get("filename") or "").strip()
        if not filename:
            missing_assets += 1
            continue
        path = asset_dir / filename
        if not path.is_file():
            missing_assets += 1
            continue
        pointer = _read_pointer(path)
        if pointer is None:
            non_pointer_assets += 1
            continue

        pointer_jobs += 1
        by_oid[pointer["oid_sha256"]].append(
            {
                "job_id": job.get("id"),
                "filename": filename,
                "page_count": job.get("page_count"),
                "last_error": job.get("last_error"),
                "lfs_size": pointer["size"],
            }
        )

    collision_groups: list[dict[str, Any]] = []
    collision_job_ids: set[str] = set()
    for oid, members in sorted(by_oid.items()):
        if len(members) < 2:
            continue
        for member in members:
            if member.get("job_id") is not None:
                collision_job_ids.add(str(member["job_id"]))
        collision_groups.append(
            {
                "oid_sha256": oid,
                "job_count": len(members),
                "jobs": sorted(members, key=lambda item: str(item.get("filename") or "")),
            }
        )

    return {
        "failed_jobs_total": len(failed_jobs),
        "failed_jobs_with_lfs_pointer": pointer_jobs,
        "failed_jobs_missing_exact_attached_asset": missing_assets,
        "failed_jobs_with_non_pointer_asset": non_pointer_assets,
        "lfs_alias_collision_groups": len(collision_groups),
        "failed_jobs_in_lfs_alias_collisions": len(collision_job_ids),
        "collisions": collision_groups,
        "evidence_is_diagnostic_only": True,
        "database_write_authorized": False,
        "registry_write_authorized": False,
        "automatic_retry_authorized": False,
        "ocr_generation_authorized": False,
        "canonicalization_authorized": False,
    }


async def _run() -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    jobs = await fetch_all(db.private_manual_import_jobs)
    result = summarize_failed_import_lfs_aliases(jobs, REPO_DIR / "attached_assets")
    print(json.dumps(result, sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Failed import LFS alias audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
