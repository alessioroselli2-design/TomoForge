#!/usr/bin/env python3
"""Dry-run Boo's Astral Menagerie structural diagnostics from private R2.

This pilot deliberately excludes page 21, which is already known to fail the
OCR quality gate. OCR source text remains in process memory only; the persisted
report contains aggregate metrics and fixed structural counters only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from reference_library import extract_reference_records
from scripts.pilot_local_ocr_from_r2 import _agreement_metrics, _run_tesseract
from scripts.pilot_local_ocr_parse_from_r2 import (
    _monster_parser_summary,
    _record_summary,
)
from services.monster_structural_diagnostics import (
    english_monster_structural_diagnostics,
)


BOOS_FILENAME = "645286721-Spelljammer-Boo-s-Astral-Menagerie-5e-pdf.pdf"
START_PAGE = 12
END_PAGE = 35
SKIPPED_PAGE = 21
SEGMENTS = ((12, 20), (22, 33), (34, 35))
MAX_SEGMENT_PAGES = 12


def _validate_segments() -> None:
    expected_pages = set(range(START_PAGE, END_PAGE + 1)) - {SKIPPED_PAGE}
    actual_pages: list[int] = []
    for segment_start, segment_end in SEGMENTS:
        if segment_start > segment_end:
            raise RuntimeError("invalid Boo's diagnostic segment")
        if segment_end - segment_start + 1 > MAX_SEGMENT_PAGES:
            raise RuntimeError("Boo's diagnostic segment exceeds 12-page safety limit")
        actual_pages.extend(range(segment_start, segment_end + 1))
    if len(actual_pages) != len(set(actual_pages)):
        raise RuntimeError("Boo's diagnostic segments overlap")
    if set(actual_pages) != expected_pages:
        raise RuntimeError(
            "Boo's diagnostic segments must cover pages 12-35 except page 21"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Boo's bounded structural OCR diagnostic"
    )
    parser.add_argument("--filename", default=BOOS_FILENAME)
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--languages", default="eng")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--comparison-psm", type=int, default=4)
    parser.add_argument("--output-dir", default="/tmp/boos-structural-diagnostic")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.psm == args.comparison_psm:
        print("OCR layout modes must differ", file=sys.stderr)
        return 2
    if args.dpi < 120 or args.dpi > 300:
        print("dpi must be 120..300", file=sys.stderr)
        return 2
    _validate_segments()

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
    all_records: list[dict] = []
    pages_needing_ocr: list[int] = []
    pages_read = 0

    with tempfile.TemporaryDirectory(prefix="tomoforge-boos-structural-") as tmp:
        tmp_path = Path(tmp)
        pdf_path = tmp_path / safe_name
        client.download_file(bucket, metadata["key"], str(pdf_path))
        document = fitz.open(pdf_path)
        page_total = document.page_count
        document.close()
        if END_PAGE > page_total:
            raise RuntimeError("diagnostic range exceeds document page count")

        scale = args.dpi / 72.0
        matrix = fitz.Matrix(scale, scale)

        def local_ocr(page: Any, page_number: int) -> str:
            if page_number == SKIPPED_PAGE:
                raise AssertionError("page 21 must never enter OCR")
            image_path = tmp_path / f"page-{page_number:04d}.png"
            page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csGRAY).save(
                image_path
            )
            primary = _run_tesseract(image_path, args.languages, args.psm)
            comparison = _run_tesseract(image_path, args.languages, args.comparison_psm)
            agreement = _agreement_metrics(primary, comparison)
            page_metrics[page_number] = agreement
            print(
                "BOOS_OCR_PAGE\t"
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

        for segment_start, segment_end in SEGMENTS:
            segment = extract_reference_records(
                pdf_path,
                local_ocr,
                segment_start,
                segment_end,
                True,
                "en",
            )
            pages_read += segment.pages_read
            pages_needing_ocr.extend(segment.pages_needing_ocr)
            all_records.extend(segment.records)

    ordered_primary_pages = sorted(primary_ocr_pages.items())
    ordered_comparison_pages = sorted(comparison_ocr_pages.items())
    monster_summary = _monster_parser_summary(
        ordered_primary_pages,
        ordered_comparison_pages,
        safe_name,
        "en",
        include_residual_single_edit=True,
    )
    structural_summary = english_monster_structural_diagnostics(
        ordered_primary_pages,
        all_records,
    )

    aggregate = {
        "filename": safe_name,
        "r2_key": metadata["key"],
        "size_bytes": metadata["size"],
        "start_page": START_PAGE,
        "end_page": END_PAGE,
        "page_count_requested": END_PAGE - START_PAGE + 1,
        "pages_explicitly_skipped": [SKIPPED_PAGE],
        "page_count_effectively_evaluated": len(page_metrics),
        "segment_count": len(SEGMENTS),
        "segments": [
            {"start_page": segment_start, "end_page": segment_end}
            for segment_start, segment_end in SEGMENTS
        ],
        "pages_read": pages_read,
        "pages_needing_ocr": sorted(set(pages_needing_ocr)),
        "quality_pages_passed": sum(
            1 for value in page_metrics.values() if value.get("quality_pass")
        ),
        "quality_pages_evaluated": len(page_metrics),
        "dpi": args.dpi,
        "languages": args.languages,
        "primary_psm": args.psm,
        "comparison_psm": args.comparison_psm,
        **_record_summary(all_records),
        **monster_summary,
        **structural_summary,
        "page_quality": [
            {"page": page, **page_metrics[page]} for page in sorted(page_metrics)
        ],
        "diagnostic_note": (
            "Pages 12-35 are covered in bounded windows. Page 21 is intentionally "
            "excluded before OCR. Structural diagnostics are aggregate-only and do "
            "not modify parser acceptance."
        ),
    }
    report_path = output_dir / "report.json"
    report_path.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "BOOS_STRUCTURAL_SUMMARY\t"
        f"quality_evaluated={aggregate['quality_pages_evaluated']}\t"
        f"quality_passed={aggregate['quality_pages_passed']}\t"
        f"records_detected={aggregate['records_detected']}\t"
        f"monster_candidates={aggregate['monster_candidates_primary']}\t"
        f"other_with_core_pair={aggregate['boos_structural_other_records_with_english_core_pair']}"
    )
    print(f"BOOS_STRUCTURAL_REPORT={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
