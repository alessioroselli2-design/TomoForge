"""Read-only Supabase connectivity diagnostic.

This script intentionally never prints secret values or row contents. It verifies
that TomoForge's runtime environment has the required backend Supabase variables
and that the service-role client can perform a minimal read through the same
client stack used by the backend.

SUPABASE_ANON_KEY is intentionally optional here: backend maintenance pipelines
must not become unavailable only because the browser/auth key is absent. The
service-role key is never substituted for the anon key (or vice versa).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping

from supabase import create_client


REQUIRED = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
OPTIONAL = ("SUPABASE_ANON_KEY",)


def _present(name: str, environ: Mapping[str, str]) -> bool:
    return bool((environ.get(name) or "").strip())


def run_diagnostic(
    *,
    environ: Mapping[str, str] | None = None,
    create_client_fn: Callable = create_client,
    emit: Callable[[str], None] = print,
) -> int:
    """Run the read-only diagnostic with injectable dependencies for safe tests."""

    env = os.environ if environ is None else environ

    emit("supabase_read_diagnostic=v2")
    for name in REQUIRED + OPTIONAL:
        emit(f"{name.lower()}={'present' if _present(name, env) else 'missing'}")

    missing = [name for name in REQUIRED if not _present(name, env)]
    if missing:
        emit("connection_result=configuration_missing")
        emit("missing_required=" + ",".join(missing))
        emit("backend_privilege_source=service_role_required_no_fallback")
        return 2

    if _present("SUPABASE_ANON_KEY", env):
        emit("anon_key_result=present_not_used_for_backend_read")
    else:
        emit("anon_key_result=missing_optional_non_blocking")
    emit("backend_privilege_source=service_role_only")

    try:
        # Deliberately construct the privileged backend client with the
        # service-role key only. SUPABASE_ANON_KEY must never be a fallback.
        client = create_client_fn(
            env["SUPABASE_URL"],
            env["SUPABASE_SERVICE_ROLE_KEY"],
        )
        result = (
            client.table("private_reference_sources")
            .select("id")
            .eq("source_status", "active")
            .limit(1)
            .execute()
        )
    except Exception as exc:  # diagnostic must classify safely without echoing secrets
        emit("connection_result=read_failed")
        emit(f"exception_type={type(exc).__name__}")
        code = getattr(exc, "code", None)
        if code is not None:
            emit(f"provider_code={code}")
        return 3

    rows = result.data or []
    emit("connection_result=read_ok")
    emit(f"active_source_probe_rows={len(rows)}")
    return 0


def main() -> int:
    return run_diagnostic()


if __name__ == "__main__":
    sys.exit(main())
