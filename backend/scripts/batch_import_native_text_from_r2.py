#!/usr/bin/env python3
"""Batch-import safe native-text Italian rule sources from private R2.

This worker is deliberately API-free: it never enables OCR or translation
providers. It is intended to drain the high-confidence, text-native Italian
portion of the recovered TomoForge corpus before any paid vision work begins.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SPELL_CARD_AIDS = frozenset({
    "Bardo .pdf",
    "Chierico.pdf",
    "Druido .pdf",
    "Mago .pdf",
    "Paladino .pdf",
    "Ranger .pdf",
    "Stregone .pdf",
    "Warlock .pdf",
})


def _eligibility_reason(filename: str, metadata: dict) -> str:
    """Return an empty string when a registered source is safe for this batch."""
    if filename in SPELL_CARD_AIDS:
        return "spell-card extraction aid"
    status = str(metadata.get("source_status") or metadata.get("status") or "").strip()
    if status and status != "active":
        return f"source status {status}"
    role = str(metadata.get("source_role") or metadata.get("role") or "").strip()
    if role in {"duplicate", "document", "excluded", "incomplete_duplicate"}:
        return f"source role {role}"
    language = str(metadata.get("language") or "").strip().lower()
    if language != "it":
        return f"language {language or 'unknown'}"
    text_mode = str(metadata.get("text_mode") or "").strip()
    if text_mode != "text":
        return f"text mode {text_mode or 'unknown'}"
    return ""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import all safe Italian native-text rule sources currently present in R2."
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=100,
        help="Maximum 12-page checkpoints per source. Default 100 (up to 1200 pages).",
    )
    parser.add_argument(
        "--target-dir",
        default="/tmp/tomoforge-native-text",
        help="Ephemeral directory used for R2 downloads.",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    # This stage must not consume OCR or translation API credits.
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)

    from reference_sources import source_is_rule_source, source_metadata_for_page
    from scripts import import_manuals_from_r2 as worker

    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals").strip() or "tomoforge-manuals"
    client = worker._r2_client()
    importable = worker._importable_r2_objects(worker._list_pdf_objects(client, bucket))

    selected: list[str] = []
    for canonical in sorted(importable):
        metadata = source_metadata_for_page(canonical)
        if not metadata or not source_is_rule_source(canonical):
            continue
        reason = _eligibility_reason(canonical, metadata)
        if not reason:
            selected.append(canonical)

    if not selected:
        print("No safe Italian native-text sources are currently present in R2.")
        return 0

    print(f"Native-text batch selected {len(selected)} source(s):")
    for filename in selected:
        print(f"  - {filename}")

    failures: list[tuple[str, str]] = []
    for index, filename in enumerate(selected, start=1):
        print(f"\n[{index}/{len(selected)}] Importing {filename}")
        worker_args = argparse.Namespace(
            filename=filename,
            max_manuals=1,
            max_chunks=args.max_chunks,
            target_dir=args.target_dir,
        )
        try:
            result = await worker._run_import(worker_args)
            if result != 0:
                failures.append((filename, f"exit code {result}"))
        except Exception as exc:  # keep later sources moving after one bad book
            message = str(exc)
            failures.append((filename, message))
            print(f"SOURCE_FAILED\t{filename}\t{message}", file=sys.stderr)

    if failures:
        print("\nNative-text batch completed with failures:", file=sys.stderr)
        for filename, message in failures:
            print(f"  - {filename}: {message}", file=sys.stderr)
        return 1

    print("\nNative-text batch completed successfully.")
    return 0


def main() -> int:
    args = _parser().parse_args()
    if args.max_chunks < 1:
        print("--max-chunks must be at least 1", file=sys.stderr)
        return 2
    try:
        return asyncio.run(_run(args))
    except Exception as exc:
        print(f"Native-text R2 batch failed before source processing: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
