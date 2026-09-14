"""Read-only Supabase connectivity diagnostic.

This script intentionally never prints secret values or row contents. It verifies
that TomoForge's runtime environment has the expected Supabase variables and that
the service-role client can perform a minimal read through the same client stack
used by the backend.
"""

from __future__ import annotations

import os
import sys

from supabase import create_client


REQUIRED = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
OPTIONAL = ("SUPABASE_ANON_KEY",)


def _present(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def main() -> int:
    print("supabase_read_diagnostic=v1")
    for name in REQUIRED + OPTIONAL:
        print(f"{name.lower()}={'present' if _present(name) else 'missing'}")

    missing = [name for name in REQUIRED if not _present(name)]
    if missing:
        print("connection_result=configuration_missing")
        print("missing_required=" + ",".join(missing))
        return 2

    try:
        client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
        result = (
            client.table("private_reference_sources")
            .select("id")
            .eq("source_status", "active")
            .limit(1)
            .execute()
        )
    except Exception as exc:  # diagnostic must classify safely without echoing secrets
        print("connection_result=read_failed")
        print(f"exception_type={type(exc).__name__}")
        code = getattr(exc, "code", None)
        if code is not None:
            print(f"provider_code={code}")
        return 3

    rows = result.data or []
    print("connection_result=read_ok")
    print(f"active_source_probe_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
