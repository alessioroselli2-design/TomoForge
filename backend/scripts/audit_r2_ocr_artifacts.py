#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import Counter

OCR_SUFFIXES = (".ocr.txt", ".ocr.json")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def classify_artifact_key(key: str) -> str | None:
    normalized = key.strip().lower()
    for suffix in OCR_SUFFIXES:
        if normalized.endswith(suffix):
            return suffix.removeprefix(".")
    return None


def main() -> int:
    import boto3
    from botocore.config import Config

    account_id = required_env("R2_ACCOUNT_ID")
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals").strip() or "tomoforge-manuals"
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=required_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=required_env("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 8, "mode": "standard"}),
    )

    artifacts: list[tuple[str, int, str]] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            artifact_type = classify_artifact_key(key)
            if artifact_type is None:
                continue
            artifacts.append((key, int(item.get("Size") or 0), artifact_type))

    artifacts.sort(key=lambda row: row[0].casefold())
    counts = Counter(kind for _, _, kind in artifacts)
    print(f"R2_OCR_ARTIFACT_COUNT={len(artifacts)}")
    print(f"R2_OCR_TOTAL_BYTES={sum(size for _, size, _ in artifacts)}")
    for kind in sorted(counts):
        print(f"R2_OCR_TYPE\t{kind}\t{counts[kind]}")
    for key, size, kind in artifacts:
        print(f"R2_OCR_ARTIFACT\t{kind}\t{size}\t{key}")
    print("R2_OCR_READ_ONLY=true")
    print("R2_OCR_DOWNLOADS_PERFORMED=0")
    print("R2_OCR_GENERATION_PERFORMED=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
