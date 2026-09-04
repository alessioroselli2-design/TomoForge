#!/usr/bin/env python3
"""Dry-run TomoForge parsing on quality-gated local OCR from a private R2 PDF.

The script never writes to Supabase and never calls hosted AI. OCR source text
exists only in process memory. The persisted report contains aggregate parser
and quality metrics, never extracted names, descriptions, or full text.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from reference_library import extract_reference_records
from scripts.pilot_local_ocr_from_r2 import _agreement_metrics, _run_tesseract
from services.monster_statblock_ocr import agreed_monster_records, parse_monster_statblocks


def _record_summary(records: list[dict]) -> dict[str, Any]:
    type_counts = Counter(str(record.get("reference_type") or "other") for record in records)
    flagged = sum(1 for record in records if record.get("review_flags"))
    ocr_flagged = sum(
        1
        for record in records
        if "ocr_da_verificare" in set(record.get("review_flags") or [])
    )
    pages = {
        int(ref.get("page"))
        for record in records
        for ref in (record.get("source_refs") or [])
        if isinstance(ref, dict) and ref.get("page") is not None
    }
    return {
        "records_detected": len(records),
        "record_types": dict(sorted(type_counts.items())),
        "records_flagged_for_review": flagged,
        "records_with_ocr_review_flag": ocr_flagged,
        "source_pages_represented": len(pages),
    }


def _monster_parser_summary(
    primary_pages: list[tuple[int, str]],
    comparison_pages: list[tuple[int, str]],
    source_filename: str,
    source_language: str,
) -> dict[str, int]:
    """Return privacy-safe aggregate metrics for the conservative monster parser."""
    primary = parse_monster_statblocks(primary_pages, source_filename, source_language)
    comparison = parse_monster_statblocks(comparison_pages, source_filename, source_language)
    agreed = agreed_monster_records(primary, comparison)
    return {
        "monster_candidates_primary": len(primary),
        "monster_candidates_comparison": len(comparison),
        "monster_candidates_independently_agreed": len(agreed),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run parser on bounded local OCR")
    parser.add_argument("--filename", required=True)
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--page-count", type=int, default=12)
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--languages", default="ita+eng")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--comparison-psm", type=int, default=4)
    parser.add_argument("--source-language", default="it")
    parser.add_argument("--output-dir", default="/tmp/local-ocr-parser-dry-run")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.start_page < 1 or args.page_count < 1 or args.page_count > 12:
        print("page_count must be 1..12", file=sys.stderr)
        return 2
    if args.psm == args.comparison_psm:
        print("OCR layout modes must differ", file=sys.stderr)
        return 2
    if args.dpi < 120 or args.dpi > 300:
        print("dpi must be 120..300", file=sys.stderr)
        return 2

    # Defense in depth against accidental paid-provider use.
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)

    import fitz
    from scripts import import_manuals_from_r2 as r2_worker

    client = r2_worker._r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals").strip() or "tomoforge-manuals"
    objects = r2_worker._list_pdf_objects(client, bucket)
    safe_name = r2_worker._safe_pdf_name(args.filename)
    metadata = objects.get(safe_name)
    if metadata is None:
        print(f"R2 PDF not found: {safe_name}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    page_metrics: dict[int, dict[str, Any]] = {}
    primary_ocr_pages: dict[int, str] = {}
    comparison_ocr_pages: dict[int, str] = {}

    with tempfile.TemporaryDirectory(prefix="tomoforge-parser-ocr-") as tmp:
        tmp_path = Path(tmp)
        pdf_path = tmp_path / safe_name
        client.download_file(bucket, metadata["key"], str(pdf_path))
        document = fitz.open(pdf_path)
        page_total = document.page_count
        document.close()
        end_page = min(page_total, args.start_page + args.page_count - 1)
        if args.start_page > page_total:
            raise RuntimeError("start page exceeds document page count")

        scale = args.dpi / 72.0
        matrix = fitz.Matrix(scale, scale)

        def local_ocr(page: Any, page_number: int) -> str:
            image_path = tmp_path / f"page-{page_number:04d}.png"
            page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csGRAY).save(image_path)
            primary = _run_tesseract(image_path, args.languages, args.psm)
            comparison = _run_tesseract(image_path, args.languages, args.comparison_psm)
            agreement = _agreement_metrics(primary, comparison)
            page_metrics[page_number] = agreement
            print(
                "PARSER_OCR_PAGE\t"
                f"{page_number}\ttoken_dice={agreement['token_dice']}\t"
                f"unique_jaccard={agreement['unique_jaccard']}\t"
                f"length_ratio={agreement['length_ratio']}\t"
                f"quality_pass={int(agreement['quality_pass'])}"
            )
            if agreement["quality_pass"]:
                primary_ocr_pages[page_number] = primary
                comparison_ocr_pages[page_number] = comparison
                return primary
            return ""

        report = extract_reference_records(
            pdf_path,
            local_ocr,
            args.start_page,
            end_page,
            True,
            args.source_language,
        )

    ordered_primary_pages = sorted(primary_ocr_pages.items())
    ordered_comparison_pages = sorted(comparison_ocr_pages.items())
    monster_summary = _monster_parser_summary(
        ordered_primary_pages,
        ordered_comparison_pages,
        safe_name,
        args.source_language,
    )

    aggregate = {
        "filename": safe_name,
        "r2_key": metadata["key"],
        "size_bytes": metadata["size"],
        "start_page": args.start_page,
        "end_page": end_page,
        "page_count_requested": args.page_count,
        "pages_read": report.pages_read,
        "pages_needing_ocr": list(report.pages_needing_ocr),
        "quality_pages_passed": sum(
            1 for value in page_metrics.values() if value.get("quality_pass")
        ),
        "quality_pages_evaluated": len(page_metrics),
        "dpi": args.dpi,
        "languages": args.languages,
        "primary_psm": args.psm,
        "comparison_psm": args.comparison_psm,
        **_record_summary(report.records),
        **monster_summary,
        "page_quality": [
            {"page": page, **page_metrics[page]}
            for page in sorted(page_metrics)
        ],
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "PARSER_SUMMARY\t"
        f"pages_read={aggregate['pages_read']}\t"
        f"quality_passed={aggregate['quality_pages_passed']}\t"
        f"records_detected={aggregate['records_detected']}\t"
        f"flagged={aggregate['records_flagged_for_review']}\t"
        f"monster_agreed={aggregate['monster_candidates_independently_agreed']}"
    )
    print(f"PARSER_REPORT={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
