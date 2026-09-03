#!/usr/bin/env python3
"""Import TomoForge private manuals from a private Cloudflare R2 bucket.

The PDF bytes are downloaded only inside the worker's ephemeral filesystem.
Vercel serves the web app; this worker handles the long-running PDF/OCR work.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _safe_pdf_name(value: str) -> str:
    name = Path(str(value or "")).name
    if not name or name in {".", ".."} or not name.lower().endswith(".pdf"):
        raise ValueError(f"Not a PDF object: {value!r}")
    return name


def _canonical_filename(filename: str) -> str:
    from reference_sources import canonical_physical_filename

    return canonical_physical_filename(filename)


def _r2_client() -> Any:
    """Build an S3-compatible client without adding boto3 to the Vercel bundle."""
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:  # pragma: no cover - workflow dependency guard
        raise RuntimeError("boto3 is required for the R2 import worker") from exc

    account_id = _required_env("R2_ACCOUNT_ID")
    endpoint = os.getenv(
        "R2_ENDPOINT",
        f"https://{account_id}.r2.cloudflarestorage.com",
    ).strip()
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=_required_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_required_env("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 8, "mode": "standard"},
        ),
    )


def _list_pdf_objects(client: Any, bucket: str) -> dict[str, dict[str, Any]]:
    """Map unique PDF basenames to R2 metadata."""
    paginator = client.get_paginator("list_objects_v2")
    objects: dict[str, dict[str, Any]] = {}
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            if not key.lower().endswith(".pdf"):
                continue
            name = _safe_pdf_name(key)
            previous = objects.get(name)
            if previous and previous["key"] != key:
                raise RuntimeError(
                    f"R2 contains duplicate PDF basenames: "
                    f"{previous['key']!r} and {key!r}"
                )
            objects[name] = {
                "key": key,
                "last_modified": item.get("LastModified"),
                "size": int(item.get("Size") or 0),
            }
    return objects


def _importable_r2_objects(
    objects: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return canonical source filename -> R2 object metadata."""
    from reference_sources import source_is_rule_source

    importable: dict[str, dict[str, Any]] = {}
    for name, metadata in sorted(objects.items()):
        canonical = _canonical_filename(name)
        if not source_is_rule_source(canonical):
            continue
        if canonical in importable and importable[canonical]["key"] != metadata["key"]:
            raise RuntimeError(
                f"R2 contains multiple objects for canonical source {canonical!r}"
            )
        importable[canonical] = {
            **metadata,
            "object_name": name,
            "canonical": canonical,
        }
    return importable


async def _infer_owner_id(db: Any) -> str:
    """Infer the single library owner without publishing an account identifier."""
    owners: set[str] = set()

    jobs = await db.private_manual_import_jobs.find({}).to_list(2000)
    owners.update(
        str(row.get("user_id") or "")
        for row in jobs
        if row.get("user_id")
    )

    if not owners:
        offset = 0
        while True:
            page = await db.private_reference_records.find({}).to_list(1000, offset)
            owners.update(
                str(row.get("user_id") or "")
                for row in page
                if row.get("user_id")
            )
            if len(page) < 1000:
                break
            offset += 1000

    owners.discard("")
    if len(owners) != 1:
        raise RuntimeError(
            "Cannot safely infer the private-library owner; "
            f"expected exactly one owner, found {len(owners)}. "
            "Set TOMOFORGE_LIBRARY_USER_ID for this worker."
        )
    return next(iter(owners))


async def _owner_id(db: Any) -> str:
    explicit = os.getenv("TOMOFORGE_LIBRARY_USER_ID", "").strip()
    return explicit or await _infer_owner_id(db)


async def _existing_source_state(
    db: Any,
    user_id: str,
) -> tuple[set[str], dict[str, dict[str, str]]]:
    """Return imported canonical sources plus one durable job per canonical source."""
    imported: set[str] = set()
    offset = 0
    while True:
        page = await db.private_reference_records.find(
            {"user_id": user_id}
        ).to_list(1000, offset)
        for row in page:
            source_key = str(row.get("source_key") or "").strip()
            if source_key:
                imported.add(_canonical_filename(source_key))
            for ref in row.get("source_refs") or []:
                filename = str(ref.get("filename") or "").strip()
                if filename:
                    imported.add(_canonical_filename(filename))
        if len(page) < 1000:
            break
        offset += 1000

    jobs: dict[str, dict[str, str]] = {}
    for job in await db.private_manual_import_jobs.find(
        {"user_id": user_id}
    ).to_list(2000):
        filename = str(job.get("filename") or "").strip()
        if not filename:
            continue
        canonical = _canonical_filename(filename)
        candidate = {
            "filename": filename,
            "status": str(job.get("status") or ""),
            "updated_at": str(job.get("updated_at") or ""),
        }
        current = jobs.get(canonical)
        if current is None or candidate["updated_at"] >= current["updated_at"]:
            jobs[canonical] = candidate
    return imported, jobs


def _pending_sources(
    importable: dict[str, dict[str, Any]],
    imported: set[str],
    jobs: dict[str, dict[str, str]],
) -> list[str]:
    pending: list[str] = []
    for canonical in sorted(importable):
        job = jobs.get(canonical)
        if job and job.get("status") != "completed":
            pending.append(canonical)
        elif canonical not in imported:
            pending.append(canonical)
    return pending


def _local_filename_for_source(
    canonical: str,
    jobs: dict[str, dict[str, str]],
) -> str:
    """Reuse a legacy alias job name so an existing durable job resumes in place."""
    job = jobs.get(canonical) or {}
    filename = str(job.get("filename") or "").strip()
    return _safe_pdf_name(filename or canonical)


def _resolve_requested_source(
    requested: str,
    importable: dict[str, dict[str, Any]],
) -> str:
    canonical = _canonical_filename(_safe_pdf_name(requested))
    if canonical not in importable:
        raise RuntimeError(
            f"Requested manual {requested!r} is not an importable PDF in R2"
        )
    return canonical


def _stable_mtime(value: Any) -> float | None:
    if isinstance(value, datetime):
        return value.timestamp()
    return None


def _download_source(
    client: Any,
    bucket: str,
    object_metadata: dict[str, Any],
    local_filename: str,
    target_dir: Path,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / _safe_pdf_name(local_filename)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.unlink(missing_ok=True)

    client.download_file(bucket, object_metadata["key"], str(temporary))
    if not temporary.is_file() or temporary.stat().st_size <= 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"R2 download produced an empty file for {local_filename}")

    expected_size = int(object_metadata.get("size") or 0)
    if expected_size and temporary.stat().st_size != expected_size:
        actual_size = temporary.stat().st_size
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"R2 size mismatch for {local_filename}: "
            f"expected {expected_size}, downloaded {actual_size}"
        )

    temporary.replace(target)
    mtime = _stable_mtime(object_metadata.get("last_modified"))
    if mtime is not None:
        os.utime(target, (mtime, mtime))
    return target


async def _run_import(args: argparse.Namespace) -> int:
    target_dir = Path(
        os.getenv("REFERENCE_MANUAL_DIRECTORY", args.target_dir)
    ).expanduser().resolve()
    os.environ["REFERENCE_MANUAL_DIRECTORY"] = str(target_dir)

    # core.config reads REFERENCE_MANUAL_DIRECTORY at import time.
    from core.db import db
    from schemas.library import ManualPreloadInput
    from services.preload import ensure_manual_preload_jobs, run_manual_preload_worker

    if not db.configured:
        raise RuntimeError("Supabase is not configured for the import worker")

    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals").strip() or "tomoforge-manuals"
    client = _r2_client()
    importable = _importable_r2_objects(_list_pdf_objects(client, bucket))
    if not importable:
        raise RuntimeError("No registered importable PDF sources were found in R2")

    user_id = await _owner_id(db)
    imported, jobs = await _existing_source_state(db, user_id)
    pending = _pending_sources(importable, imported, jobs)

    if args.filename:
        selected = [_resolve_requested_source(args.filename, importable)]
    else:
        selected = pending[: args.max_manuals]

    if not selected:
        print("No pending manual sources remain.")
        return 0

    print(
        f"R2 worker: {len(importable)} importable PDFs available; "
        f"{len(pending)} pending; processing {len(selected)}."
    )

    for canonical in selected:
        metadata = importable[canonical]
        local_filename = _local_filename_for_source(canonical, jobs)
        print(
            f"Downloading {metadata['object_name']} from R2 "
            f"as {local_filename}..."
        )
        local_path = _download_source(
            client,
            bucket,
            metadata,
            local_filename,
            target_dir,
        )
        print(f"Downloaded {local_path.name} ({local_path.stat().st_size} bytes).")

        await ensure_manual_preload_jobs(
            user_id,
            ManualPreloadInput(filename=local_filename, retry=True),
            db=db,
        )
        await run_manual_preload_worker(user_id, db=db)

        job = await db.private_manual_import_jobs.find_one(
            {"user_id": user_id, "filename": local_filename}
        )
        status = str((job or {}).get("status") or "")
        if status != "completed":
            error = str((job or {}).get("last_error") or "unknown")
            raise RuntimeError(
                f"Manual import did not complete for {local_filename}: "
                f"status={status or 'missing'}, error={error}"
            )

        local_path.unlink(missing_ok=True)
        print(f"Completed {local_filename}.")

    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download private manuals from Cloudflare R2 and run the "
            "durable TomoForge importer."
        )
    )
    parser.add_argument(
        "--filename",
        default="",
        help="Specific R2/registered PDF filename. Default: next pending source.",
    )
    parser.add_argument(
        "--max-manuals",
        type=int,
        default=1,
        help="Maximum pending sources to process when --filename is omitted.",
    )
    parser.add_argument(
        "--target-dir",
        default="/tmp/tomoforge-manuals",
        help="Ephemeral directory used for the current worker run.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.max_manuals < 1:
        print("--max-manuals must be at least 1", file=sys.stderr)
        return 2
    try:
        return asyncio.run(_run_import(args))
    except Exception as exc:
        print(f"R2 manual import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
