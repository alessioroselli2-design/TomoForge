#!/usr/bin/env python3
"""Read-only OCR audit for the four source-guided repairs blocked by HP gates."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.repair_monsters_from_source import (
    SourcePdfCache,
    _candidate_matches_target,
    _fetch_all,
    _ocr_source_window,
    resolve_source,
)
from services.monster_statblock_ocr import parse_monster_statblocks
from services.ocr_semantic_gates import monster_semantic_numeric_flags

TARGETS: tuple[dict[str, str], ...] = (
    {"id": "ref_d3a9aeba19775d698d1dae2577086c2e", "name": "Di Terra"},
    {"id": "ref_b5a471157553590992c4b3af5c57deda", "name": "Fraz-Urb'Luu"},
    {
        "id": "ref_650f39bad9ac50c3a9d2ffcfde535f45",
        "name": "Lavamandra Warlock Di Imix",
    },
    {"id": "ref_94dd0655e7fc518aaf9e3ad214e0dba7", "name": "Quetzalcoatlus"},
)


def _core_excerpt(text: str) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines() if line.strip()]
    anchor = next(
        (
            index
            for index, line in enumerate(lines)
            if line.casefold().startswith("classe armatura")
            or line.casefold().startswith("classe d'armatura")
        ),
        None,
    )
    if anchor is None:
        return "\n".join(lines[:10])
    start = max(0, anchor - 2)
    end = min(len(lines), anchor + 4)
    return "\n".join(lines[start:end])


def _matching_candidates(
    pages: list[tuple[int, str]],
    source_filename: str,
    source_language: str,
    target_name: str,
    target_page: int,
) -> list[dict[str, Any]]:
    parsed = parse_monster_statblocks(
        pages,
        source_filename,
        source_language,
    )
    return [
        record
        for record in parsed
        if _candidate_matches_target(
            record,
            target_name,
            target_page,
        )
    ]


async def _run(args: argparse.Namespace) -> int:
    # Defense in depth: this audit is local OCR only.
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)

    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records = db.private_reference_records
    sources = await _fetch_all(
        db.private_reference_sources,
        {"source_status": "active"},
    )
    pdf_cache = SourcePdfCache(
        args.pdf_root,
        args.allow_r2_download,
    )
    reports: list[dict[str, Any]] = []
    try:
        for expected in TARGETS:
            record = await records.find_one({"id": expected["id"]})
            if record is None:
                raise RuntimeError(f"Missing target {expected['id']}")
            if str(record.get("name") or "") != expected["name"]:
                raise RuntimeError(f"Target name drift: {expected['id']}")
            if str(record.get("review_status") or "") != "verified":
                raise RuntimeError(f"Target status drift: {expected['id']}")
            if record.get("canonical_id"):
                raise RuntimeError(f"Target canonicalized: {expected['id']}")

            source, source_ref = resolve_source(record, sources)
            target_page = int(source_ref["page"])
            pdf_path = pdf_cache.get(source)
            primary_pages, comparison_pages, quality = _ocr_source_window(
                pdf_path,
                target_page,
                int(source["physical_pages"]),
                source,
                dpi=args.dpi,
                languages=args.languages,
                psm=args.psm,
                comparison_psm=args.comparison_psm,
            )

            primary_matches = _matching_candidates(
                primary_pages,
                str(source["physical_filename"]),
                str(source.get("language") or "it"),
                expected["name"],
                target_page,
            )
            comparison_matches = _matching_candidates(
                comparison_pages,
                str(source["physical_filename"]),
                str(source.get("language") or "it"),
                expected["name"],
                target_page,
            )

            reports.append(
                {
                    "id": expected["id"],
                    "name": expected["name"],
                    "source": {
                        "physical_filename": source.get("physical_filename"),
                        "physical_page": target_page,
                        "logical_page": source_ref.get("logical_page"),
                        "logical_source_id": source.get("logical_source_id"),
                    },
                    "layout": {
                        "profile": quality[target_page]["layout_profile"],
                        "effective_dpi": quality[target_page]["effective_dpi"],
                        "primary_psm": quality[target_page]["primary_psm"],
                        "comparison_psm": quality[target_page]["comparison_psm"],
                    },
                    "primary_match_count": len(primary_matches),
                    "comparison_match_count": len(comparison_matches),
                    "primary": [
                        {
                            "attributes": match.get("attributes") or {},
                            "gate_flags": sorted(
                                monster_semantic_numeric_flags(
                                    match.get("attributes") or {}
                                )
                            ),
                            "raw_core_excerpt": _core_excerpt(
                                match.get("full_text") or ""
                            ),
                        }
                        for match in primary_matches
                    ],
                    "comparison": [
                        {
                            "attributes": match.get("attributes") or {},
                            "gate_flags": sorted(
                                monster_semantic_numeric_flags(
                                    match.get("attributes") or {}
                                )
                            ),
                            "raw_core_excerpt": _core_excerpt(
                                match.get("full_text") or ""
                            ),
                        }
                        for match in comparison_matches
                    ],
                    "writes_performed": 0,
                }
            )
    finally:
        pdf_cache.close()

    print("FINAL_REPORT")
    print(
        json.dumps(
            {
                "dry_run": True,
                "targets": len(TARGETS),
                "writes_performed": 0,
                "reports": reports,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only raw OCR audit for four failed-gate monsters"
    )
    parser.add_argument("--pdf-root", default=os.getenv("TOMOFORGE_PDF_ROOT", ""))
    parser.add_argument("--allow-r2-download", action="store_true")
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--languages", default="ita")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--comparison-psm", type=int, default=4)
    return parser


def main() -> int:
    try:
        return asyncio.run(_run(_parser().parse_args()))
    except Exception as exc:
        print(f"Failed-gate OCR audit aborted: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
