"""Aggregate bounded, independently vetted Van Richten OCR windows.

Each source window is processed in its own independent OCR/parser invocation
with at most 12 physical pages. This module reads metrics-only JSON reports;
it never reads the original PDF or private OCR text and cannot write records.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SOURCE_ID = "vrgr_2021_it"
WINDOWS = ((177, 188), (189, 200), (213, 224), (225, 236), (237, 248), (249, 257))
PREVIOUSLY_AUDITED = (201, 212)
WRITES = 0
EXPECTED_STATUS = "source_ocr_candidate_only_not_verified_not_importable"
CANDIDATE_FIELDS = frozenset({
    "name", "physical_page", "core_fields",
    "independent_ocr_agreement", "manual_review_required",
})
CORE_FIELDS = frozenset({"classe_armatura", "punti_ferita", "velocita"})


def validate_windows() -> None:
    pages: list[int] = []
    for start, end in WINDOWS:
        if not 1 <= start <= end <= 257 or end - start + 1 > 12:
            raise ValueError("ocr_window_limit_violation")
        pages.extend(range(start, end + 1))
    if len(pages) != len(set(pages)):
        raise ValueError("ocr_windows_overlap")
    other = set(range(PREVIOUSLY_AUDITED[0], PREVIOUSLY_AUDITED[1] + 1))
    if set(pages) & other or set(pages) | other != set(range(177, 258)):
        raise ValueError("ocr_page_coverage_gap")


def window_filename(start: int, end: int) -> str:
    return f"vrgr-{start}-{end}.json"


def combine_readonly_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    validate_windows()
    if len(reports) != len(WINDOWS):
        raise ValueError("missing_window_reports")
    all_candidates: list[dict] = []
    totals = {
        "pages_quality_pass": 0,
        "pages_quality_failed": 0,
        "independently_agreed_candidates": 0,
        "blocked_invalid_hit_dice": 0,
    }
    for (start, end), report in zip(WINDOWS, reports, strict=True):
        if (
            report.get("logical_source_id") != SOURCE_ID
            or report.get("source_sha256_matched") is not True
            or report.get("database_writes") != 0
            or report.get("status") != EXPECTED_STATUS
            or report.get("start_page") != start
            or report.get("end_page") != end
        ):
            raise ValueError("untrusted_or_misplaced_window_report")
        passes = report.get("quality_pass_pages")
        fails = report.get("quality_failed_pages")
        if (
            not isinstance(passes, list)
            or not isinstance(fails, list)
            or sorted(passes + fails) != list(range(start, end + 1))
        ):
            raise ValueError("window_quality_coverage_gap")
        totals["pages_quality_pass"] += len(passes)
        totals["pages_quality_failed"] += len(fails)
        totals["independently_agreed_candidates"] += int(
            report.get("independently_agreed_candidates") or 0
        )
        totals["blocked_invalid_hit_dice"] += len(
            report.get("blocked_invalid_hit_dice") or []
        )
        for item in report.get("candidates_for_manual_review") or []:
            if (
                not isinstance(item, dict)
                or set(item) != CANDIDATE_FIELDS
                or set(item.get("core_fields") or {}) != CORE_FIELDS
                or not item.get("independent_ocr_agreement")
                or not item.get("manual_review_required")
                or not start <= item.get("physical_page", -1) <= end
                or not isinstance(item.get("name"), str)
                or not 1 <= len(item["name"]) <= 80
            ):
                raise ValueError("candidate_provenance_or_field_gate")
            all_candidates.append(item)

    counts: dict[str, int] = {}
    for record in all_candidates:
        identity = " ".join(record["name"].casefold().split())
        counts[identity] = counts.get(identity, 0) + 1
    repeated_names = sorted({name for name, count in counts.items() if count > 1})
    candidate_names = [
        {"name": record["name"], "physical_page": record["physical_page"],
         "core_fields": record["core_fields"], "manual_review_required": True}
        for record in all_candidates
        if counts[" ".join(record["name"].casefold().split())] == 1
    ]
    return {
        "logical_source_id": SOURCE_ID,
        "status": "bounded_ocr_survey_only_manual_review_required",
        "windows": [{"start": s, "end": e} for s, e in WINDOWS],
        **totals,
        "source_candidate_names": candidate_names,
        "cross_window_duplicate_names_blocked": repeated_names,
        "any_database_writes": WRITES,
        "ready_for_canonical_import": False,
        "previously_audited_pages": list(PREVIOUSLY_AUDITED),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validate_windows()
    reports = [
        json.loads((args.input_dir / window_filename(s, e)).read_text(encoding="utf-8"))
        for s, e in WINDOWS
    ]
    summary = combine_readonly_reports(reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("VRGR_READONLY_SURVEY " + json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
