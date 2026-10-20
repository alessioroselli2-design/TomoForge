#!/usr/bin/env python3
"""Combine bounded local OCR pilot reports without exposing source OCR text.

Input reports are already privacy-safe aggregate JSON. This combiner keeps the
same property: it sums only aggregate counters, merges record-type counts, and
concatenates per-page quality metrics. It never reads or emits OCR source text.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

_ADDITIVE_KEYS = {
    "pages_read",
    "quality_pages_passed",
    "quality_pages_evaluated",
    "records_detected",
    "records_flagged_for_review",
    "records_with_ocr_review_flag",
    "source_pages_represented",
}


def _is_additive_counter(key: str, value: object) -> bool:
    return isinstance(value, int) and (
        key in _ADDITIVE_KEYS or key.startswith("monster_")
    )


def combine_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        raise ValueError("at least one report is required")

    filename = str(reports[0].get("filename") or "")
    r2_key = str(reports[0].get("r2_key") or "")
    if not filename or not r2_key:
        raise ValueError("reports must include filename and r2_key")
    if any(str(report.get("filename") or "") != filename for report in reports):
        raise ValueError("all reports must refer to the same filename")
    if any(str(report.get("r2_key") or "") != r2_key for report in reports):
        raise ValueError("all reports must refer to the same r2_key")

    totals: Counter[str] = Counter()
    record_types: Counter[str] = Counter()
    page_quality: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []

    for report in reports:
        for key, value in report.items():
            if _is_additive_counter(key, value):
                totals[key] += int(value)
        for key, value in (report.get("record_types") or {}).items():
            if isinstance(value, int):
                record_types[str(key)] += value
        for item in report.get("page_quality") or []:
            if isinstance(item, dict):
                page_quality.append(dict(item))
        windows.append(
            {
                "start_page": int(report.get("start_page") or 0),
                "end_page": int(report.get("end_page") or 0),
                "page_count_requested": int(report.get("page_count_requested") or 0),
                "quality_pages_passed": int(report.get("quality_pages_passed") or 0),
                "quality_pages_evaluated": int(
                    report.get("quality_pages_evaluated") or 0
                ),
                "monster_candidates_primary": int(
                    report.get("monster_candidates_primary") or 0
                ),
                "monster_candidates_comparison": int(
                    report.get("monster_candidates_comparison") or 0
                ),
                "monster_candidates_independently_agreed": int(
                    report.get("monster_candidates_independently_agreed") or 0
                ),
                "monster_candidates_guided_core_merged": int(
                    report.get("monster_candidates_guided_core_merged") or 0
                ),
            }
        )

    starts = [window["start_page"] for window in windows if window["start_page"] > 0]
    ends = [window["end_page"] for window in windows if window["end_page"] > 0]
    result: dict[str, Any] = {
        "sample_mode": "bounded_multi_window",
        "filename": filename,
        "r2_key": r2_key,
        "size_bytes": int(reports[0].get("size_bytes") or 0),
        "start_page": min(starts) if starts else 0,
        "end_page": max(ends) if ends else 0,
        "page_count_requested_total": sum(
            window["page_count_requested"] for window in windows
        ),
        "window_count": len(windows),
        "windows": windows,
        "record_types": dict(sorted(record_types.items())),
        "page_quality": sorted(
            page_quality, key=lambda item: int(item.get("page") or 0)
        ),
        "aggregation_note": (
            "Counts are summed across non-overlapping bounded windows; no raw OCR text is persisted."
        ),
    }
    result.update(dict(sorted(totals.items())))
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Combine privacy-safe bounded OCR pilot reports"
    )
    parser.add_argument("--report", action="append", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    reports = [
        json.loads(Path(path).read_text(encoding="utf-8")) for path in args.report
    ]
    combined = combine_reports(reports)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"COMBINED_PARSER_REPORT={output}")
    print(
        "COMBINED_PARSER_SUMMARY\t"
        f"windows={combined['window_count']}\t"
        f"pages={combined['page_count_requested_total']}\t"
        f"monster_agreed={combined.get('monster_candidates_independently_agreed', 0)}\t"
        f"guided={combined.get('monster_candidates_guided_core_merged', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
