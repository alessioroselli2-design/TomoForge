"""Read-only R2 OCR candidate audit for one Italian Van Richten window.

Candidates are potential source blocks for manual review, never canonical
creatures. Only short factual identities and core numeric fields may appear
in the report: no scans, raw OCR, abilities prose, or complete text.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scripts.pilot_local_ocr_from_r2 import _agreement_metrics, _run_tesseract
from scripts.vrgr_r2_source_preflight import (
    EXPECTED_PAGES,
    EXPECTED_SHA256,
    FILENAME,
    SOURCE_ID,
    _sha256_file,
)
from services.monster_statblock_ocr import (
    agreed_monster_records,
    parse_monster_statblocks,
)

WRITES = 0
FIELDS = ("classe_armatura", "punti_ferita", "velocita")
HP_DICE_PATTERN = re.compile(r"^(\d+)\s*\((\d+)d(\d+)(?:\s*([+-])\s*(\d+))?\)$")


def hit_dice_coherent(value: str) -> bool:
    """Reject OCR-mangled dice and mathematically inconsistent HP."""
    match = HP_DICE_PATTERN.fullmatch(value.strip())
    if not match:
        return False
    average, count, sides, sign, bonus = match.groups()
    n, die = int(count), int(sides)
    if n < 1 or n > 100 or die not in {4, 6, 8, 10, 12, 20}:
        return False
    modifier = int(bonus or 0) * (-1 if sign == "-" else 1)
    return int(average) == (n * (die + 1)) // 2 + modifier



def metadata_candidate(record: dict) -> dict | None:
    """Emit minimal, bounded review-only facts; no OCR prose."""
    name = str(record.get("name") or "").strip()
    page = record.get("start_page")
    attrs = record.get("attributes") or {}
    if (
        not name
        or len(name) > 80
        or not isinstance(page, int)
        or page < 1
        or page > EXPECTED_PAGES
        or not all(isinstance(attrs.get(k), str) and 0 < len(attrs[k]) <= 140 for k in FIELDS)
        or not hit_dice_coherent(attrs.get("punti_ferita") or "")
        or "ocr_independent_agreement" not in set(record.get("review_flags") or [])
    ):
        return None
    return {
        "name": name,
        "physical_page": page,
        "core_fields": {key: attrs[key] for key in FIELDS},
        "independent_ocr_agreement": True,
        "manual_review_required": True,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start-page", type=int, required=True)
    p.add_argument("--page-count", type=int, default=12)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    if not 1 <= args.start_page <= EXPECTED_PAGES:
        raise ValueError("start_page_outside_registered_source")
    if not 1 <= args.page_count <= 12:
        raise ValueError("ocr_window_exceeds_12_page_limit")
    if args.start_page + args.page_count - 1 > EXPECTED_PAGES:
        raise ValueError("ocr_window_exceeds_registered_source")
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)

    import fitz
    from scripts import import_manuals_from_r2 as worker

    client = worker._r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals").strip()
    meta = worker._list_pdf_objects(client, bucket).get(FILENAME)
    if not meta:
        raise RuntimeError("registered_van_richten_source_missing_in_r2")

    quality = []
    primary: list[tuple[int, str]] = []
    comparison: list[tuple[int, str]] = []
    with tempfile.TemporaryDirectory(prefix="vrgr-candidate-dry-run-") as tmp:
        target = Path(tmp) / FILENAME
        client.download_file(bucket, meta["key"], str(target))
        if _sha256_file(target) != EXPECTED_SHA256:
            raise ValueError("original_van_richten_sha256_mismatch")
        with fitz.open(target) as pdf:
            if pdf.page_count != EXPECTED_PAGES:
                raise ValueError("registered_page_count_mismatch")
            for number in range(args.start_page, args.start_page + args.page_count):
                image_path = Path(tmp) / f"ocr-{number}.png"
                pdf[number - 1].get_pixmap(
                    matrix=fitz.Matrix(200 / 72, 200 / 72),
                    colorspace=fitz.csGRAY,
                    alpha=False,
                ).save(image_path)
                left = _run_tesseract(image_path, "ita", 6)
                right = _run_tesseract(image_path, "ita", 4)
                result = _agreement_metrics(left, right)
                quality.append({"page": number, "quality_pass": result["quality_pass"]})
                if result["quality_pass"]:
                    primary.append((number, left))
                    comparison.append((number, right))

    primary_candidates = parse_monster_statblocks(primary, FILENAME, "it")
    other_candidates = parse_monster_statblocks(comparison, FILENAME, "it")
    agreed = agreed_monster_records(primary_candidates, other_candidates)
    supported = [x for record in agreed if (x := metadata_candidate(record)) is not None]
    # Refuse repeated identities within the same OCR window without relying on
    # fuzzy title matching.
    counts: dict[str, int] = {}
    for item in supported:
        key = item["name"].casefold()
        counts[key] = counts.get(key, 0) + 1
    unique = [item for item in supported if counts[item["name"].casefold()] == 1]
    unique.sort(key=lambda item: (item["physical_page"], item["name"].casefold()))
    numeric_gate_blocked = [
        {"name": str(record.get("name") or "")[:80], "page": record.get("start_page")}
        for record in agreed
        if not hit_dice_coherent(
            str((record.get("attributes") or {}).get("punti_ferita") or "")
        )
    ]
    summary = {
        "logical_source_id": SOURCE_ID,
        "source_sha256_matched": True,
        "physical_pages": EXPECTED_PAGES,
        "start_page": args.start_page,
        "end_page": args.start_page + args.page_count - 1,
        "quality_pass_pages": [q["page"] for q in quality if q["quality_pass"]],
        "quality_failed_pages": [q["page"] for q in quality if not q["quality_pass"]],
        "primary_candidates": len(primary_candidates),
        "comparison_candidates": len(other_candidates),
        "independently_agreed_candidates": len(agreed),
        "unique_minimal_candidates": len(unique),
        "excluded_ambiguous_duplicates": len(supported) - len(unique),
        "blocked_invalid_hit_dice": numeric_gate_blocked,
        "candidates_for_manual_review": unique,
        "status": "source_ocr_candidate_only_not_verified_not_importable",
        "database_writes": WRITES,
    }
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("VRGR_CANDIDATE_SUMMARY " + json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
