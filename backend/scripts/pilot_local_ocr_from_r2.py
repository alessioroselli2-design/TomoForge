#!/usr/bin/env python3
"""Run a bounded, read-only local Tesseract OCR pilot on one private R2 PDF.

No Supabase writes and no external AI APIs are used. The script downloads one
manual to the ephemeral runner, renders only the requested page window, runs
local Tesseract, and writes a small JSON quality report plus per-page text files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _text_quality(text: str) -> dict[str, Any]:
    value = text or ""
    nonspace = [ch for ch in value if not ch.isspace()]
    letters = [ch for ch in nonspace if ch.isalpha()]
    printable = [ch for ch in nonspace if ch.isprintable()]
    words = re.findall(r"[^\W\d_]{2,}", value, flags=re.UNICODE)
    return {
        "chars": len(value),
        "nonspace_chars": len(nonspace),
        "letter_ratio": round(len(letters) / len(nonspace), 4) if nonspace else 0.0,
        "printable_ratio": round(len(printable) / len(nonspace), 4) if nonspace else 0.0,
        "word_count": len(words),
    }


def _run_tesseract(image_path: Path, languages: str, psm: int) -> str:
    command = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        languages,
        "--psm",
        str(psm),
        "quiet",
    ]
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded local OCR pilot for an R2 manual")
    parser.add_argument("--filename", required=True)
    parser.add_argument("--start-page", type=int, required=True, help="1-based first PDF page")
    parser.add_argument("--page-count", type=int, default=12)
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--languages", default="ita+eng")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--output-dir", default="/tmp/local-ocr-pilot")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.start_page < 1 or args.page_count < 1 or args.page_count > 24:
        print("Invalid page window; page_count must be 1..24", file=sys.stderr)
        return 2
    if args.dpi < 120 or args.dpi > 300:
        print("--dpi must be between 120 and 300", file=sys.stderr)
        return 2

    # Defense in depth: this pilot must never consume hosted AI credits.
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

    with tempfile.TemporaryDirectory(prefix="tomoforge-ocr-") as tmp:
        pdf_path = Path(tmp) / safe_name
        client.download_file(bucket, metadata["key"], str(pdf_path))
        document = fitz.open(pdf_path)
        last_page = min(document.page_count, args.start_page - 1 + args.page_count)
        if args.start_page > document.page_count:
            raise RuntimeError(
                f"start page {args.start_page} exceeds document page count {document.page_count}"
            )

        pages: list[dict[str, Any]] = []
        scale = args.dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        for page_number in range(args.start_page, last_page + 1):
            page = document.load_page(page_number - 1)
            native_text = page.get_text("text") or ""
            image_path = Path(tmp) / f"page-{page_number:04d}.png"
            page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csGRAY).save(image_path)
            ocr_text = _run_tesseract(image_path, args.languages, args.psm)
            text_path = output_dir / f"page-{page_number:04d}.txt"
            text_path.write_text(ocr_text, encoding="utf-8")
            page_report = {
                "page": page_number,
                "native": _text_quality(native_text),
                "ocr": _text_quality(ocr_text),
            }
            pages.append(page_report)
            print(
                "OCR_PAGE\t"
                f"{page_number}\tnative_chars={page_report['native']['chars']}\t"
                f"ocr_chars={page_report['ocr']['chars']}\t"
                f"ocr_letter_ratio={page_report['ocr']['letter_ratio']}\t"
                f"ocr_words={page_report['ocr']['word_count']}"
            )
        document.close()

    report = {
        "filename": safe_name,
        "r2_key": metadata["key"],
        "size_bytes": metadata["size"],
        "start_page": args.start_page,
        "page_count_requested": args.page_count,
        "page_count_processed": len(pages),
        "dpi": args.dpi,
        "languages": args.languages,
        "psm": args.psm,
        "pages": pages,
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OCR_REPORT={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
