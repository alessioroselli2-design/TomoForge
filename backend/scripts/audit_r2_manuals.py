#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
from collections import defaultdict


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


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

    rows = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            if not key.lower().endswith(".pdf"):
                continue
            size = int(item.get("Size") or 0)
            digest = hashlib.sha256()
            response = client.get_object(Bucket=bucket, Key=key)
            body = response["Body"]
            while True:
                chunk = body.read(8 * 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
            body.close()
            sha = digest.hexdigest()
            rows.append((key, size, sha))

    rows.sort(key=lambda x: x[0].casefold())
    print(f"R2_PDF_COUNT={len(rows)}")
    print(f"R2_TOTAL_BYTES={sum(size for _, size, _ in rows)}")
    for key, size, sha in rows:
        print(f"R2_FILE\t{size}\t{sha}\t{key}")

    by_sha = defaultdict(list)
    for key, size, sha in rows:
        by_sha[(size, sha)].append(key)
    duplicate_groups = [names for names in by_sha.values() if len(names) > 1]
    print(f"R2_DUPLICATE_GROUPS={len(duplicate_groups)}")
    for i, names in enumerate(duplicate_groups, 1):
        print(f"R2_DUPLICATE_{i}\t" + "\t".join(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
