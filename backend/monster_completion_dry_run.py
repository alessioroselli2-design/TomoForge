"""Offline JSON preflight report; never connects to Supabase or writes records.

Usage:
    python backend/monster_completion_dry_run.py original.json candidate.json

This is deliberately a *dry-run only*. Evidence flags must be provided by a
separate review process; command-line execution cannot certify a source page.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from monster_completion_preflight import preflight


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only monster completion check")
    parser.add_argument("original", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    original = json.loads(args.original.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    if not isinstance(original, dict) or not isinstance(candidate, dict):
        parser.error("Both files must contain one JSON object")
    # Deliberately refuse to assert evidence or review automatically.
    result = preflight(original, candidate)
    print(json.dumps({
        "record_id": original.get("id"),
        "ready": result.ready,
        "blockers": list(result.blockers),
        "fingerprint": result.proposed_fingerprint,
        "writes_performed": 0,
    }, ensure_ascii=False, indent=2))
    return 0 if result.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
