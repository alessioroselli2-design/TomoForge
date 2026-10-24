#!/usr/bin/env python3
"""Source-page OCR recovery for three fragmented Eberron dragonmarks.

Run only on GitHub Actions with private R2 and Supabase credentials.
Original PDF/OCR stays on the runner or in the original owner's private DB.
This restores source evidence, never accepts or approves any race card.
Each page is an independent one-page OCR window.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SOURCE = "618795464-Eberron.pdf"
PDF_SHA256 = "525e94622d502067d3e045f28e696759003cc360f2e7fd57364f13fc5b0731d5"
PAGE_COUNT = 322
SCHEMA_VERSION = "eberron-three-private-page-evidence-v1"
TARGETS = (
    {
        "id": "ref_001bfa782bc957dfb82af701dd84ecd2",
        "name": "Marchio Dell'Addestramento",
        "page": 41, "old_sha": "668cdc755161ff048fa3707db9fa1df6727116e83f42badffc2e9dcd998192fe",
        "labels": ("Intuito Selvaggio", "Legame Primordiale",
                   "Più Grossi Sono", "Incantesimi del Marchio"),
    },
    {
        "id": "ref_869c9da2b48659909e6bee212adc9a33",
        "name": "Marchio Della Guarigione",
        "page": 43, "old_sha": "af7b3da0b0db5746b4163556957e029e76b4e48df0f3599c6a1d2a4b9bda2a1f",
        "labels": ("Intuito Medico", "Tocco Guaritore", "Incantesimi del Marchio"),
    },
    {
        "id": "ref_7782a337888a576d9e17491eb1e35676",
        "name": "Marchio Della Sentinella",
        "page": 51, "old_sha": "9e3462882ed9ac0cbda78adc90bc1d75d50be8df75296765917af61be9fb00f9",
        "labels": ("Intuito della Sentinella", "Scudo del Guardiano",
                   "Guardiano Vigile", "Incantesimi del Marchio"),
    },
)


def normalize(s: str) -> str:
    x = unicodedata.normalize("NFKD", str(s or "").casefold())
    return re.sub(r"\s+", " ", "".join(ch for ch in x if not unicodedata.combining(ch))).strip()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def relevant_evidence(text: str, target: dict) -> dict:
    lowered = normalize(text)
    heading = normalize(target["name"]).replace("marchio ", "")
    all_labels = {label: normalize(label) in lowered for label in target["labels"]}
    return {
        "heading": heading in lowered,
        "score_heading": "incremento dei punteggi di caratteristica" in lowered,
        "labels": all_labels,
        "characters": len(text),
    }


def gate(primary: str, comparison: str, target: dict) -> bool:
    a = relevant_evidence(primary, target)
    b = relevant_evidence(comparison, target)
    return bool(
        1200 <= len(primary) <= 20000
        and 1200 <= len(comparison) <= 20000
        and a["heading"] and b["heading"]
        and a["score_heading"] and b["score_heading"]
        and all(a["labels"].values())
        and all(b["labels"].values())
    )


def _ocr(page, directory: Path, page_number: int, mode: int, crop: bool) -> str:
    import pymupdf

    bounds = page.rect
    rects = (
        (
            pymupdf.Rect(bounds.x0, bounds.y0, bounds.x0 + bounds.width * 0.53, bounds.y1),
            pymupdf.Rect(bounds.x0 + bounds.width * 0.47, bounds.y0, bounds.x1, bounds.y1),
        ) if crop else (bounds,)
    )
    texts: list[str] = []
    for i, rect in enumerate(rects):
        image = directory / f"source-{page_number}-psm{mode}-{i}.png"
        page.get_pixmap(
            matrix=pymupdf.Matrix(1.8, 1.8),
            colorspace=pymupdf.csGRAY, alpha=False, clip=rect,
        ).save(image)
        try:
            result = subprocess.run(
                ["tesseract", str(image), "stdout", "-l", "ita", "--psm", str(mode)],
                capture_output=True, text=True, check=False, timeout=75,
            )
            texts.append(result.stdout if result.returncode == 0 else "")
        except (OSError, subprocess.TimeoutExpired):
            texts.append("")
        finally:
            image.unlink(missing_ok=True)
    return "\n".join(texts)


def recover_source(pdf_path: Path) -> list[dict]:
    import pymupdf

    if sha256(pdf_path.read_bytes()) != PDF_SHA256:
        raise RuntimeError("registered_eberron_pdf_hash_mismatch")
    results = []
    with pymupdf.open(pdf_path) as pdf:
        if pdf.page_count != PAGE_COUNT:
            raise RuntimeError("registered_eberron_pdf_page_count_mismatch")
        with tempfile.TemporaryDirectory(prefix="three-eberron-source-pages-") as folder:
            for target in TARGETS:
                page = pdf[target["page"] - 1]
                primary = _ocr(page, Path(folder), target["page"], 4, crop=False)
                comparison = _ocr(page, Path(folder), target["page"], 6, crop=True)
                passed = gate(primary, comparison, target)
                results.append({
                    "target": target,
                    "passed": passed,
                    "page_sha256": sha256(primary.encode("utf-8")) if passed else "",
                    "page_source_text": primary if passed else "",
                    "labels_found": sum(relevant_evidence(primary, target)["labels"].values()),
                    "labels_expected": len(target["labels"]),
                })
    return results


def _safe_row(row: dict, target: dict) -> bool:
    old = str(row.get("source_full_text") or "")
    refs = row.get("source_refs") or []
    return bool(
        row.get("id") == target["id"]
        and row.get("source_key") == SOURCE
        and row.get("name") == target["name"]
        and row.get("reference_type") == "subrace"
        and row.get("review_status") == "verified"
        and row.get("ai_review_status") == "pending"
        and row.get("source_text_checksum") == target["old_sha"]
        and 0 < len(old) < 500
        and any(isinstance(ref, dict) and ref.get("filename") == SOURCE
                and str(ref.get("page")) == str(target["page"]) for ref in refs)
    )


def execute(results: list[dict], *, write: bool) -> list[dict]:
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    token = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not token:
        raise RuntimeError("private_supabase_read_credentials_missing")
    db = create_client(url, token)
    report = []
    for item in results:
        target = item["target"]
        record = db.table("private_reference_records").select(
            "id,user_id,source_key,name,reference_type,review_status,ai_review_status,"
            "source_text_checksum,source_full_text,source_refs,attributes,review_notes"
        ).eq("id", target["id"]).execute().data
        original = record[0] if record and len(record) == 1 else {}
        matched = item["passed"] and _safe_row(original, target)
        outcome = "not_eligible"
        if matched:
            outcome = "source_found_not_written"
            if write:
                old = original["source_full_text"]
                attrs = dict(original.get("attributes") or {})
                if "source_original_fragment_before_recovery" in attrs:
                    raise RuntimeError("previous_original_fragment_already_archived")
                attrs["source_original_fragment_before_recovery"] = {
                    "text": old,
                    "checksum": target["old_sha"],
                    "recovered_from": "partial_preexisting_2019_ocr",
                }
                attrs["source_ocr_recovery_20261024"] = {
                    "source_filename": SOURCE, "physical_page": target["page"],
                    "pdf_sha256": PDF_SHA256,
                    "ocr_method": "tesseract_psm4_full_verified_against_psm6_columns",
                    "scope": "one_original_pdf_page_not_entire_rules_section",
                    "semantic_review_completed": False,
                }
                note = (str(original.get("review_notes") or "") +
                        "\n2026-10-24: original page OCR restored privately from SHA-sealed R2 "
                        f"page {target['page']}; original truncated fragment archived; "
                        "AI status unchanged; semantic review still required.")
                change = {
                    "source_full_text": item["page_source_text"],
                    "source_text_checksum": item["page_sha256"],
                    "attributes": attrs,
                    "review_notes": note,
                }
                saved = (db.table("private_reference_records").update(change)
                    .eq("id", target["id"])
                    .eq("user_id", original["user_id"])
                    .eq("source_key", SOURCE)
                    .eq("source_text_checksum", target["old_sha"])
                    .eq("ai_review_status", "pending")
                    .execute().data)
                if not saved or len(saved) != 1:
                    raise RuntimeError("private_original_source_fingerprint_write_failed")
                outcome = "source_restored_review_pending"
                readback = (db.table("private_reference_records")
                    .select("source_text_checksum,ai_review_status,review_status")
                    .eq("id", target["id"]).execute().data)
                if (not readback or len(readback) != 1
                    or readback[0]["source_text_checksum"] != item["page_sha256"]
                    or readback[0]["ai_review_status"] != "pending"
                    or readback[0]["review_status"] != "verified"):
                    raise RuntimeError("private_original_source_readback_failed")
        report.append({
            "page": target["page"], "target_id": target["id"],
            "source_gate_passed": item["passed"],
            "original_snapshot_matched": bool(matched),
            "labels_found": item["labels_found"],
            "labels_expected": item["labels_expected"],
            "result": outcome,
        })
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(name, None)
    from scripts.import_manuals_from_r2 import _list_pdf_objects, _r2_client

    r2 = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    metadata = _list_pdf_objects(r2, bucket).get(SOURCE)
    if not metadata or not 0 < metadata["size"] < 600 * 1024 * 1024:
        raise RuntimeError("registered_eberron_source_missing")
    with tempfile.TemporaryDirectory(prefix="private-eberron-source-") as tmp:
        pdf = Path(tmp) / SOURCE
        r2.download_file(bucket, metadata["key"], str(pdf))
        results = recover_source(pdf)
        summaries = execute(results, write=args.execute)
    report = {
        "schema": SCHEMA_VERSION,
        "sha256_matched": True,
        "one_page_ocr_windows": 3,
        "source_ocr_recovery": summaries,
        "requested_writes": bool(args.execute),
        "ai_verifications_performed": 0,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("EBERRON_THREE_PRIVATE_SOURCE_RECOVERY " + json.dumps({
        "executed": args.execute,
        "restored": sum(x["result"] == "source_restored_review_pending" for x in summaries),
        "not_eligible": sum(x["result"] == "not_eligible" for x in summaries),
        "ai_verifications_performed": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
