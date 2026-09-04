#!/usr/bin/env python3
"""Import a tiny, quality-gated local-OCR window from one private R2 manual.

This is intentionally stricter than the normal preload worker:
- at most 3 PDF pages per run;
- Tesseract only, with two independent layout modes;
- no OpenAI/Gemini credentials or calls;
- every OCR-derived record remains review-gated;
- no canonicalization is performed;
- source PDF and rendered images stay on the ephemeral runner.

The existing importer is reused for provenance/deduplication. Its internal OCR
hook is replaced for this process only; if that replacement ever failed, the
hosted-provider API keys are explicitly blank, so the run fails closed rather
than spending credits.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts import import_manuals_from_r2 as r2_worker
from scripts.pilot_local_ocr_from_r2 import _agreement_metrics, _run_tesseract

_MAX_PAGES = 3
_OCR_REVISION = "local-tesseract-dual-psm-v1"


def _validate_page_window(start_page: int, page_count: int) -> tuple[int, int]:
    if start_page < 1:
        raise ValueError("start_page must be >= 1")
    if page_count < 1 or page_count > _MAX_PAGES:
        raise ValueError(f"page_count must be 1..{_MAX_PAGES}")
    return start_page, start_page + page_count - 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded local OCR import from private R2")
    parser.add_argument("--filename", required=True)
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--page-count", type=int, default=3)
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--languages", default="ita+eng")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--comparison-psm", type=int, default=4)
    parser.add_argument("--target-dir", default="/tmp/tomoforge-local-ocr-import")
    parser.add_argument("--report", default="/tmp/tomoforge-local-ocr-import-report.json")
    return parser


async def _run(args: argparse.Namespace) -> int:
    start_page, end_page = _validate_page_window(args.start_page, args.page_count)
    if args.dpi < 120 or args.dpi > 300:
        raise ValueError("dpi must be 120..300")
    if args.psm == args.comparison_psm:
        raise ValueError("primary and comparison OCR layout modes must differ")

    # Defense in depth: this worker must never consume hosted AI credits.
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["GEMINI_API_KEY"] = ""

    target_dir = Path(args.target_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    os.environ["REFERENCE_MANUAL_DIRECTORY"] = str(target_dir)

    # Import config/services only after the ephemeral manual directory and blank
    # hosted-provider keys are fixed for this process.
    from core.db import db
    from schemas.library import ReferenceImportInput
    from services import library as library_service

    if not db.configured:
        raise RuntimeError("Supabase is not configured for the local OCR worker")

    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals").strip() or "tomoforge-manuals"
    client = r2_worker._r2_client()
    objects = r2_worker._list_pdf_objects(client, bucket)
    safe_name = r2_worker._safe_pdf_name(args.filename)
    metadata = objects.get(safe_name)
    if metadata is None:
        raise RuntimeError(f"R2 PDF not found: {safe_name}")

    user_id = await r2_worker._owner_id(db)
    local_path = r2_worker._download_source(
        client,
        bucket,
        metadata,
        safe_name,
        target_dir,
    )

    quality_by_page: dict[int, dict[str, Any]] = {}
    try:
        page_count = library_service.manual_page_count(local_path)
        if not page_count:
            raise RuntimeError("Could not determine PDF page count")
        if start_page > page_count:
            raise RuntimeError(
                f"start page {start_page} exceeds document page count {page_count}"
            )
        bounded_end_page = min(end_page, page_count)

        scale = args.dpi / 72.0
        with tempfile.TemporaryDirectory(prefix="tomoforge-live-local-ocr-") as image_dir:
            image_root = Path(image_dir)

            def local_ocr(page: Any, page_number: int, source_language: str = "") -> str:
                image_path = image_root / f"page-{page_number:04d}.png"
                # Use the page's own PyMuPDF pixmap API, avoiding source bytes in logs/artifacts.
                import pymupdf as fitz

                page.get_pixmap(
                    matrix=fitz.Matrix(scale, scale),
                    alpha=False,
                    colorspace=fitz.csGRAY,
                ).save(image_path)
                primary = _run_tesseract(image_path, args.languages, args.psm)
                comparison = _run_tesseract(image_path, args.languages, args.comparison_psm)
                agreement = _agreement_metrics(primary, comparison)
                quality_by_page[page_number] = agreement
                print(
                    "LOCAL_OCR_PAGE\t"
                    f"{page_number}\ttoken_dice={agreement['token_dice']}\t"
                    f"unique_jaccard={agreement['unique_jaccard']}\t"
                    f"length_ratio={agreement['length_ratio']}\t"
                    f"quality_pass={int(agreement['quality_pass'])}"
                )
                return primary if agreement["quality_pass"] else ""

            # The existing service only exposes its hosted-OCR hook internally.
            # Swap that hook for this process so persistence/dedup/provenance stay
            # on the battle-tested code path while no hosted provider is reachable.
            original_ocr = library_service.openai_ocr_manual_page
            library_service.openai_ocr_manual_page = local_ocr
            try:
                result = await library_service.import_private_reference_manuals(
                    user_id,
                    ReferenceImportInput(
                        filenames=[safe_name],
                        start_page=start_page,
                        end_page=bounded_end_page,
                        use_ai_ocr=True,
                        # Required by the legacy service guard. No external OCR is
                        # actually used because the hook above is local-only.
                        external_processing_confirmed=True,
                        translation_processing_confirmed=False,
                        auto_accept=False,
                    ),
                    db=db,
                )
            finally:
                library_service.openai_ocr_manual_page = original_ocr

        source_report = next(
            (source for source in result.sources if source.get("filename") == safe_name),
            {},
        )
        evaluated = sorted(quality_by_page)
        failed_quality_pages = [
            page for page in evaluated
            if not quality_by_page[page].get("quality_pass")
        ]
        unresolved_pages = sorted(set(source_report.get("pages_needing_ocr") or []))

        # Add durable, non-text provenance to newly imported/updated records for
        # this exact source/page window. Never expose the extracted text here.
        records = await db.private_reference_records.find(
            {"user_id": user_id, "source_key": safe_name}
        ).to_list(5000)
        touched = 0
        for record in records:
            refs = [ref for ref in (record.get("source_refs") or []) if isinstance(ref, dict)]
            if not any(
                start_page <= int(ref.get("page") or 0) <= bounded_end_page
                for ref in refs
            ):
                continue
            changed = False
            updated_refs = []
            for ref in refs:
                page = int(ref.get("page") or 0)
                updated_ref = dict(ref)
                if start_page <= page <= bounded_end_page:
                    updated_ref.update({
                        "extraction_mode": "local_ocr",
                        "ocr_provider": "tesseract",
                        "ocr_revision": _OCR_REVISION,
                        "ocr_languages": args.languages,
                        "ocr_dpi": args.dpi,
                        "ocr_primary_psm": args.psm,
                        "ocr_comparison_psm": args.comparison_psm,
                        "ocr_quality_pass": bool(
                            quality_by_page.get(page, {}).get("quality_pass")
                        ),
                    })
                    changed = changed or updated_ref != ref
                updated_refs.append(updated_ref)
            if changed:
                flags = sorted(set(record.get("review_flags") or []) | {"ocr_da_verificare"})
                await db.private_reference_records.update_one(
                    {"id": record["id"], "user_id": user_id},
                    {"$set": {
                        "source_refs": updated_refs,
                        "review_flags": flags,
                        "review_status": "needs_review",
                    }},
                )
                touched += 1

        report = {
            "filename": safe_name,
            "r2_key": metadata["key"],
            "size_bytes": metadata["size"],
            "start_page": start_page,
            "end_page": bounded_end_page,
            "pages_quality_evaluated": len(evaluated),
            "pages_quality_passed": len(evaluated) - len(failed_quality_pages),
            "quality_failed_pages": failed_quality_pages,
            "pages_needing_ocr": unresolved_pages,
            "records_detected": int(source_report.get("records_detected") or 0),
            "records_imported": int(result.imported),
            "records_updated": int(result.updated),
            "records_flagged": int(result.flagged_for_review),
            "records_skipped": int(result.skipped),
            "records_with_local_ocr_provenance": touched,
            "ocr_revision": _OCR_REVISION,
        }
        Path(args.report).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            "LOCAL_OCR_IMPORT_SUMMARY\t"
            f"quality_passed={report['pages_quality_passed']}/{report['pages_quality_evaluated']}\t"
            f"detected={report['records_detected']}\t"
            f"imported={report['records_imported']}\t"
            f"updated={report['records_updated']}\t"
            f"flagged={report['records_flagged']}\t"
            f"provenance={report['records_with_local_ocr_provenance']}"
        )
        if failed_quality_pages or unresolved_pages:
            raise RuntimeError(
                "Local OCR live pilot did not pass every page; no further automatic expansion is allowed"
            )
        return 0
    finally:
        local_path.unlink(missing_ok=True)


def main() -> int:
    args = _parser().parse_args()
    try:
        return asyncio.run(_run(args))
    except Exception as exc:
        print(f"Local OCR import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
