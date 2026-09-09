#!/usr/bin/env python3
"""Run bounded, non-persistent parser probes against native PDF text only.

These diagnostics intentionally bypass the database and every external provider.
They invoke the deterministic parser with no OCR callback, never translate,
never import records, and cap each probe (or a set of windows) at 12 pages.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from reference_library import CHARACTER_CREATION_REFERENCE_TYPES, ReferenceImportReport, extract_reference_records

MAX_PROBE_PAGES = 12


def bounded_native_text_parser_probe(
    pdf_path: Path,
    *,
    start_page: int,
    end_page: int,
    source_language: str,
    extractor: Callable[..., ReferenceImportReport] = extract_reference_records,
) -> dict[str, Any]:
    """Return parser metrics without OCR, translation, persistence, or mutation."""
    pdf_path = Path(pdf_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("probe target must be a PDF")
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)
    if start_page < 1 or end_page < start_page:
        raise ValueError("invalid probe page range")
    requested_pages = end_page - start_page + 1
    if requested_pages > MAX_PROBE_PAGES:
        raise ValueError(f"probe is limited to {MAX_PROBE_PAGES} pages")

    report = extractor(pdf_path, None, start_page, end_page, False, source_language)
    record_signals = [
        (
            str(record.get("reference_type") or "other"),
            str(record.get("name") or "").strip(),
        )
        for record in report.records
    ]
    counts = Counter(reference_type for reference_type, _ in record_signals)
    named_counts = Counter(reference_type for reference_type, name in record_signals if name)
    named_records = sum(named_counts.values())
    useful_named_records = sum(
        count for reference_type, count in named_counts.items() if reference_type in CHARACTER_CREATION_REFERENCE_TYPES
    )
    non_useful_named_records = named_records - useful_named_records
    names = [name for _, name in record_signals]

    return {
        "source_filename": pdf_path.name,
        "source_language": source_language,
        "start_page": start_page,
        "end_page": end_page,
        "requested_pages": requested_pages,
        "pages_read": int(report.pages_read),
        "pages_needing_ocr": sorted(int(page) for page in report.pages_needing_ocr),
        "native_text_pages_available": int(report.pages_read),
        "records_detected": len(report.records),
        "named_records_detected": named_records,
        "unnamed_records_detected": len(report.records) - named_records,
        "record_types": dict(sorted(counts.items())),
        "named_record_types": dict(sorted(named_counts.items())),
        "useful_named_records_detected": useful_named_records,
        "non_useful_named_records_detected": non_useful_named_records,
        "useful_named_share": useful_named_records / named_records if named_records else 0.0,
        "useful_named_signal_is_complete": named_records > 0 and non_useful_named_records == 0,
        "sample_record_names": [name for name in names if name][:10],
        "pdf_bytes_read": True,
        "bounded_native_text_parser_probe_executed": True,
        "ocr_callback_supplied": False,
        "ocr_used": False,
        "translation_used": False,
        "external_processing_used": False,
        "database_read_used": False,
        "database_write_used": False,
        "records_persisted": False,
        "review_state_mutated": False,
        "canonicalization_performed": False,
        "automatic_import_authorized": False,
    }


def bounded_native_text_parser_probe_windows(
    pdf_path: Path,
    *,
    windows: Iterable[tuple[int, int]],
    source_language: str,
    extractor: Callable[..., ReferenceImportReport] = extract_reference_records,
) -> dict[str, Any]:
    """Measure several tiny windows separately while enforcing one 12-page budget."""
    normalized_windows = tuple((int(start), int(end)) for start, end in windows)
    if not normalized_windows:
        raise ValueError("at least one probe window is required")

    total_requested_pages = 0
    for start_page, end_page in normalized_windows:
        if start_page < 1 or end_page < start_page:
            raise ValueError("invalid probe page range")
        total_requested_pages += end_page - start_page + 1
    if total_requested_pages > MAX_PROBE_PAGES:
        raise ValueError(f"combined probe windows are limited to {MAX_PROBE_PAGES} pages")

    window_results: list[dict[str, Any]] = []
    aggregate_types: Counter[str] = Counter()
    aggregate_named_types: Counter[str] = Counter()
    for index, (start_page, end_page) in enumerate(normalized_windows, start=1):
        result = bounded_native_text_parser_probe(
            pdf_path,
            start_page=start_page,
            end_page=end_page,
            source_language=source_language,
            extractor=extractor,
        )
        aggregate_types.update(result["record_types"])
        aggregate_named_types.update(result["named_record_types"])
        window_results.append({"window_index": index, **result})

    records_detected_total = sum(result["records_detected"] for result in window_results)
    named_records_total = sum(result["named_records_detected"] for result in window_results)
    useful_named_records_total = sum(result["useful_named_records_detected"] for result in window_results)
    non_useful_named_records_total = named_records_total - useful_named_records_total
    productive_windows = sum(result["records_detected"] > 0 for result in window_results)
    named_signal_windows = sum(result["named_records_detected"] > 0 for result in window_results)
    ranked_windows = sorted(
        (
            {
                "window_index": result["window_index"],
                "start_page": result["start_page"],
                "end_page": result["end_page"],
                "records_detected": result["records_detected"],
                "named_records_detected": result["named_records_detected"],
                "unnamed_records_detected": result["unnamed_records_detected"],
                "record_types": result["record_types"],
                "named_record_types": result["named_record_types"],
                "useful_named_records_detected": result["useful_named_records_detected"],
                "non_useful_named_records_detected": result["non_useful_named_records_detected"],
                "useful_named_share": result["useful_named_share"],
                "useful_named_signal_is_complete": result["useful_named_signal_is_complete"],
            }
            for result in window_results
        ),
        key=lambda result: (-result["named_records_detected"], result["unnamed_records_detected"], result["window_index"]),
    )
    best_named_signal_window = ranked_windows[0] if ranked_windows else None
    best_window_dominant_reference_type = None
    best_window_dominant_reference_type_count = 0
    if best_named_signal_window and best_named_signal_window["record_types"]:
        best_window_dominant_reference_type, best_window_dominant_reference_type_count = sorted(
            best_named_signal_window["record_types"].items(),
            key=lambda item: (-item[1], item[0]),
        )[0]

    best_window_useful_named_records_detected = (
        best_named_signal_window["useful_named_records_detected"] if best_named_signal_window else 0
    )
    best_window_non_useful_named_records_detected = (
        best_named_signal_window["non_useful_named_records_detected"] if best_named_signal_window else 0
    )
    best_window_useful_named_share = best_named_signal_window["useful_named_share"] if best_named_signal_window else 0.0
    best_window_useful_named_signal_is_complete = (
        best_named_signal_window["useful_named_signal_is_complete"] if best_named_signal_window else False
    )

    return {
        "source_filename": Path(pdf_path).name,
        "source_language": source_language,
        "window_count": len(window_results),
        "requested_pages_total": total_requested_pages,
        "records_detected_total": records_detected_total,
        "named_records_detected_total": named_records_total,
        "unnamed_records_detected_total": records_detected_total - named_records_total,
        "useful_named_records_detected_total": useful_named_records_total,
        "non_useful_named_records_detected_total": non_useful_named_records_total,
        "useful_named_share_total": useful_named_records_total / named_records_total if named_records_total else 0.0,
        "useful_named_signal_is_complete_total": named_records_total > 0 and non_useful_named_records_total == 0,
        "productive_windows": productive_windows,
        "named_signal_windows": named_signal_windows,
        "empty_windows": len(window_results) - productive_windows,
        "record_types_total": dict(sorted(aggregate_types.items())),
        "named_record_types_total": dict(sorted(aggregate_named_types.items())),
        "windows": window_results,
        "windows_by_named_signal": ranked_windows,
        "best_named_signal_window": best_named_signal_window,
        "best_window_dominant_reference_type": best_window_dominant_reference_type,
        "best_window_dominant_reference_type_count": best_window_dominant_reference_type_count,
        "best_window_useful_named_records_detected": best_window_useful_named_records_detected,
        "best_window_non_useful_named_records_detected": best_window_non_useful_named_records_detected,
        "best_window_useful_named_share": best_window_useful_named_share,
        "best_window_useful_named_signal_is_complete": best_window_useful_named_signal_is_complete,
        "ranking_is_diagnostic_only": True,
        "best_window_selection_is_diagnostic_only": True,
        "dominant_type_is_diagnostic_only": True,
        "useful_named_share_is_diagnostic_only": True,
        "useful_named_signal_completeness_is_diagnostic_only": True,
        "ocr_used": False,
        "translation_used": False,
        "external_processing_used": False,
        "database_read_used": False,
        "database_write_used": False,
        "records_persisted": False,
        "review_state_mutated": False,
        "canonicalization_performed": False,
        "automatic_import_authorized": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe at most 12 PDF pages using only TomoForge native-text parser logic.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument("--source-language", default="es")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = bounded_native_text_parser_probe(
            args.pdf_path,
            start_page=args.start_page,
            end_page=args.end_page,
            source_language=args.source_language.strip().lower() or "unknown",
        )
    except Exception as exc:
        print(f"Bounded native-text parser probe failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
