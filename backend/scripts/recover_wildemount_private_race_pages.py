#!/usr/bin/env python3
"""Recover only corroborated physical Wildemount race pages from private R2.

A recovered page is evidence, not a semantic approval. Never alter source OCR
already present, AI status, translations, or the original PDF. Reports contain
only identifiers, page numbers and booleans, not copyrighted page text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SOURCE = "469650052-Explorer-s-Guide-to-Wildemount-pdf.pdf"
SHA256 = "15b34ddd1b33832fe2169821974d3a8d2de8470679ec49225e7e8669f029ce76"
PDF_PAGES = 307
# id, Italian name, type, original heading, *physical* page, original trait headings
TARGETS = (
    ("ref_75787591ecc1b55014d8316fed281382", "Elfo Pallido",
     "subrace", "Pallid Elf", 164, ("Incisive Sense", "Blessing of the Moon Weaver")),
    ("ref_b00b7572a9bc7ab88a1d664d461da45c", "Halfling Lotusden",
     "subrace", "Lotusden Halfling", 165, ("Child of the Wood", "Timberwalk")),
    ("ref_db3671677af43a4ef4abd00dbaf956d6", "Dragonide Draconblood",
     "subrace", "Draconblood", 169, ("Forceful Presence", "Darkvision")),
    ("ref_5e64ebb844f153c7229fc51ffcd62158", "Dragonide Ravenita",
     "subrace", "Ravenite", 169, ("Vengeful Assault", "Darkvision")),
    ("ref_ca9b0146819f42804fab0b65b44728a9", "Orco di Exandria",
     "race", "Orc", 177, ("Aggressive", "Powerful Build", "Primal Intuition")),
)


def old_record_gate(row: dict, target: tuple) -> bool:
    refs = row.get("source_refs") or []
    attributes = row.get("attributes") or {}
    return bool(
        row.get("id") == target[0]
        and row.get("name") == target[1]
        and row.get("reference_type") == target[2]
        and row.get("source_key") == SOURCE
        and row.get("review_status") == "verified"
        and row.get("ai_review_status") == "pending"
        and not row.get("source_full_text")
        and not row.get("source_text_checksum")
        and "original_pdf_page_ocr_recovered" not in attributes
        and any(
            isinstance(ref, dict)
            and ref.get("filename") == SOURCE
            and str(ref.get("page")) == str(target[4])
            and (ref.get("sha256") or ref.get("physical_sha256")) == SHA256
            for ref in refs
        )
    )


def inspect_pdf(path: Path) -> list[dict]:
    import pymupdf
    from scripts.recover_five_race_source_pages import accepted, ocr, sha256

    if sha256(path) != SHA256:
        raise RuntimeError("private_original_sha256_mismatch")
    result = []
    with pymupdf.open(path) as pdf:
        if pdf.page_count != PDF_PAGES:
            raise RuntimeError("private_original_page_count_mismatch")
        with tempfile.TemporaryDirectory(prefix="wildemount-ocr-") as tmp:
            cache = {}
            for target in TARGETS:
                number = target[4]
                if number not in cache:
                    page = pdf[number - 1]
                    cache[number] = (
                        page.get_text("text", sort=True),
                        ocr(page, Path(tmp), number, 4),
                        ocr(page, Path(tmp), number, 6),
                    )
                native, p4, p6 = cache[number]
                # accepted() demands a title and at least two independent
                # target-specific feature labels in BOTH readings.
                use_native = accepted(native, p4, (None, None, target[3], None, target[5]))
                primary = native if use_native else p4
                second = p4 if use_native else p6
                accepted_page = accepted(primary, second, (None, None, target[3], None, target[5]))
                result.append({
                    "target": target,
                    "passed": accepted_page,
                    "text": primary if accepted_page else "",
                    "checksum": hashlib.sha256(primary.encode()).hexdigest() if accepted_page else "",
                    "method": "native_and_psm4" if use_native else "psm4_and_psm6",
                })
    return result


def persist(items: list[dict], *, execute: bool) -> list[dict]:
    from supabase import create_client

    url, secret = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not secret:
        raise RuntimeError("private_database_credentials_missing")
    db = create_client(url, secret)
    report = []
    for item in items:
        target = item["target"]
        found = (
            db.table("private_reference_records")
            .select("id,user_id,name,reference_type,source_key,review_status,"
                    "ai_review_status,source_full_text,source_text_checksum,"
                    "source_refs,attributes")
            .eq("id", target[0]).execute().data
        )
        old = found[0] if found and len(found) == 1 else {}
        eligible = bool(item["passed"] and old_record_gate(old, target))
        status = "blocked_source_or_snapshot"
        if eligible:
            status = "safe_dry_run"
            if execute:
                attributes = dict(old.get("attributes") or {})
                attributes["original_pdf_page_ocr_recovered"] = {
                    "source_pdf_sha256": SHA256,
                    "physical_page": target[4],
                    "scope": "one_original_page_not_approved_rules",
                    "method": item["method"],
                    "semantic_review_completed": False,
                }
                changed = (
                    db.table("private_reference_records")
                    .update({
                        "source_full_text": item["text"],
                        "source_text_checksum": item["checksum"],
                        "attributes": attributes,
                    })
                    .eq("id", target[0])
                    .eq("user_id", old["user_id"])
                    .eq("source_key", SOURCE)
                    .eq("reference_type", target[2])
                    .eq("review_status", "verified")
                    .eq("ai_review_status", "pending")
                    .eq("source_text_checksum", "")
                    .execute().data
                )
                if not changed or len(changed) != 1:
                    raise RuntimeError("fingerprinted_private_write_failed")
                readback = (
                    db.table("private_reference_records")
                    .select("source_text_checksum,review_status,ai_review_status")
                    .eq("id", target[0]).execute().data
                )
                if (
                    not readback or len(readback) != 1
                    or readback[0]["source_text_checksum"] != item["checksum"]
                    or readback[0]["review_status"] != "verified"
                    or readback[0]["ai_review_status"] != "pending"
                ):
                    raise RuntimeError("private_source_readback_failed")
                status = "source_page_restored_ai_pending"
        report.append({
            "id": target[0],
            "name": target[1],
            "physical_page": target[4],
            "source_gate": item["passed"],
            "record_gate": eligible,
            "result": status,
        })
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    for secret in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(secret, None)
    from scripts.import_manuals_from_r2 import _r2_client, _list_pdf_objects

    r2 = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    item = _list_pdf_objects(r2, bucket).get(SOURCE)
    if not item or not 0 < item["size"] < 600 * 1024 * 1024:
        raise RuntimeError("registered_private_source_unavailable")
    with tempfile.TemporaryDirectory(prefix="wildemount-private-source-") as tmp:
        path = Path(tmp) / "original.pdf"
        r2.download_file(bucket, item["key"], str(path))
        observations = inspect_pdf(path)
        outcomes = persist(observations, execute=args.execute)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "schema": "wildemount-private-source-evidence-v1",
        "result": outcomes,
        "executed": args.execute,
        "ai_updates": 0,
        "source_text_emitted": False,
        "max_ocr_window_pages": 1,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WILDEMOUNT_SOURCE_RECOVERY " + json.dumps({
        "executed": args.execute,
        "source_gates": sum(x["source_gate"] for x in outcomes),
        "restored": sum(x["result"] == "source_page_restored_ai_pending" for x in outcomes),
        "ai_updates": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
