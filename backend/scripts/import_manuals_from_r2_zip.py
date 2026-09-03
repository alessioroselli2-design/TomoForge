#!/usr/bin/env python3
"""Expand one TomoForge PDF bundle already uploaded to private Cloudflare R2.

The archive is downloaded in GitHub Actions, validated, and each PDF is copied
back to the bucket as its original basename. Existing objects are preserved by
default. The character sheet is stored under resources/ instead of being fed to
the rules importer. No OCR/import work is performed here.
"""
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def r2_client():
    import boto3
    from botocore.config import Config

    account_id = required_env("R2_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=required_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=required_env("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 8, "mode": "standard"}),
    )


def safe_member_name(raw: str) -> str:
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe ZIP member: {raw!r}")
    name = path.name.strip()
    if not name or not name.lower().endswith(".pdf"):
        return ""
    return name


def target_key(filename: str) -> str:
    if filename.casefold() == "scheda personaggio .pdf".casefold():
        return f"resources/character-sheet/{filename}"
    return filename


def object_exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except client.exceptions.ClientError as exc:
        status = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) or 0)
        if status == 404:
            return False
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip-key", required=True, help="R2 object key for the uploaded ZIP")
    parser.add_argument("--overwrite", action="store_true", help="Replace objects already present")
    parser.add_argument("--delete-zip", action="store_true", help="Delete the source ZIP after success")
    args = parser.parse_args()

    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals").strip() or "tomoforge-manuals"
    client = r2_client()

    with tempfile.TemporaryDirectory(prefix="tomoforge-r2-zip-") as tmp:
        tmpdir = Path(tmp)
        archive = tmpdir / "bundle.zip"
        client.download_file(bucket, args.zip_key, str(archive))
        if not zipfile.is_zipfile(archive):
            raise RuntimeError(f"R2 object {args.zip_key!r} is not a valid ZIP archive")

        uploaded = 0
        skipped_existing = 0
        skipped_non_pdf = 0
        seen_targets: set[str] = set()

        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                filename = safe_member_name(info.filename)
                if not filename:
                    skipped_non_pdf += 1
                    continue
                key = target_key(filename)
                if key in seen_targets:
                    raise RuntimeError(f"ZIP contains duplicate PDF target name: {filename!r}")
                seen_targets.add(key)

                if not args.overwrite and object_exists(client, bucket, key):
                    print(f"KEEP existing: {key}")
                    skipped_existing += 1
                    continue

                local = tmpdir / filename
                with zf.open(info, "r") as source, local.open("wb") as destination:
                    shutil.copyfileobj(source, destination, length=8 * 1024 * 1024)
                if local.stat().st_size <= 0:
                    raise RuntimeError(f"Empty PDF in ZIP: {filename}")

                client.upload_file(
                    str(local),
                    bucket,
                    key,
                    ExtraArgs={"ContentType": "application/pdf"},
                )
                print(f"UPLOADED: {key} ({local.stat().st_size} bytes)")
                uploaded += 1
                local.unlink(missing_ok=True)

        print(
            f"ZIP expansion complete: uploaded={uploaded}, "
            f"existing_kept={skipped_existing}, non_pdf_skipped={skipped_non_pdf}."
        )

    if args.delete_zip:
        client.delete_object(Bucket=bucket, Key=args.zip_key)
        print(f"Deleted source ZIP: {args.zip_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
