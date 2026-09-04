#!/usr/bin/env python3
"""Read-only audit of versioned source metadata versus Supabase catalogue rows."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


COMPARE_FIELDS = (
    "language",
    "ruleset",
    "authority_class",
    "source_role",
    "source_status",
    "text_mode",
    "notes",
)


def _segment_key(row: dict) -> tuple[str, str, int, int]:
    return (
        str(row.get("physical_filename") or ""),
        str(row.get("logical_source_id") or ""),
        int(row.get("page_start") or 1),
        int(row.get("page_end") or 0),
    )


def _expected_row(segment: dict) -> dict:
    return {
        "physical_filename": str(segment["physical_filename"]),
        "logical_source_id": str(segment["logical_source_id"]),
        "page_start": int(segment.get("page_start") or 1),
        "page_end": int(segment.get("page_end") or 0),
        "language": str(segment.get("language") or ""),
        "ruleset": str(segment.get("ruleset") or ""),
        "authority_class": str(segment.get("authority_class") or ""),
        "source_role": str(segment.get("role") or ""),
        "source_status": str(segment.get("status") or ""),
        "text_mode": str(segment.get("text_mode") or ""),
        "notes": str(segment.get("notes") or ""),
    }


def _diff(expected: dict, actual: dict) -> dict[str, tuple[str, str]]:
    drift: dict[str, tuple[str, str]] = {}
    for field in COMPARE_FIELDS:
        wanted = str(expected.get(field) or "")
        found = str(actual.get(field) or "")
        if wanted != found:
            drift[field] = (found, wanted)
    return drift


async def _run() -> int:
    from core.db import db
    from reference_sources import SOURCE_SEGMENTS

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    rows = await db.private_reference_sources.find({}).to_list(5000)
    expected = {_segment_key(_expected_row(segment)): _expected_row(segment) for segment in SOURCE_SEGMENTS}
    actual = {_segment_key(row): row for row in rows}

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    drifted: list[tuple[tuple[str, str, int, int], dict[str, tuple[str, str]]]] = []

    for key in sorted(set(expected) & set(actual)):
        differences = _diff(expected[key], actual[key])
        if differences:
            drifted.append((key, differences))

    print(f"SOURCE_REGISTRY_EXPECTED={len(expected)}")
    print(f"SOURCE_REGISTRY_ACTUAL={len(actual)}")
    print(f"SOURCE_REGISTRY_MISSING={len(missing)}")
    print(f"SOURCE_REGISTRY_EXTRA={len(extra)}")
    print(f"SOURCE_REGISTRY_DRIFTED={len(drifted)}")

    for key in missing:
        print("MISSING\t" + "\t".join(map(str, key)))
    for key in extra:
        print("EXTRA\t" + "\t".join(map(str, key)))
    for key, differences in drifted:
        filename, logical_id, page_start, page_end = key
        for field, (found, wanted) in sorted(differences.items()):
            print(
                "DRIFT\t"
                f"{filename}\t{logical_id}\t{page_start}\t{page_end}\t"
                f"{field}\tCURRENT={found!r}\tEXPECTED={wanted!r}"
            )

    # Drift is an audit finding, not a workflow failure. The output is used to
    # decide whether a controlled reconciliation migration is warranted.
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"Source-registry drift audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
