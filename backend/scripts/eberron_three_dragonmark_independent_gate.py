#!/usr/bin/env python3
"""Read-only comparison of three Eberron dragonmarks with owner's R2 PDF.

At most three physical pages. No PDF/OCR/rule prose in artifacts or logs.
No Supabase writes. A lexical pass is NOT full semantic verification.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from scripts.eberron_three_dragonmark_fields import (  # noqa: E402
    EXPECTED_PAGES, EXPECTED_SHA256, SOURCE, TARGETS, ocr_text, sha256,
)

IDS = {
    41: "ref_001bfa782bc957dfb82af701dd84ecd2",
    43: "ref_869c9da2b48659909e6bee212adc9a33",
    51: "ref_7782a337888a576d9e17491eb1e35676",
}
STATS = {"FOR": "forza", "DES": "destrezza", "COS": "costituzione",
         "INT": "intelligenza", "SAG": "saggezza", "CAR": "carisma"}


def fold(text):
    text = unicodedata.normalize("NFKD", str(text).casefold())
    return re.sub(r"\s+", " ", "".join(c for c in text if not unicodedata.combining(c))).strip()


def phrase(text, target):
    target = fold(target)
    return bool(target and re.search(r"(?<!\w)" + re.escape(target) + r"(?!\w)", fold(text)))


def score(text, stat, increase):
    if stat not in STATS or increase not in (1, 2):
        return False
    pattern = (r"\b" + STATS[stat] + r"\b.{0,85}?\b"
               r"(?:aumenta|incrementa|aumentato|aumentata)\b"
               r".{0,24}?\b(?:di\s+)?" + str(increase) + r"\b")
    return bool(re.search(pattern, fold(text)))


def compare(row, readings, mark):
    attrs = row.get("attributes") or {}
    checks = {}

    def add(name, votes):
        checks[name] = {"votes": votes, "passed": votes >= 2}

    add("heading", sum(phrase(t, mark) for t in readings.values()))
    for stat, value in sorted((attrs.get("incremento_caratteristiche") or {}).items()):
        add("ability_" + stat, sum(score(t, stat, value) for t in readings.values()))
    traits = attrs.get("tratti_razziali") or []
    if not isinstance(traits, list) or not traits:
        add("traits_missing", 0)
    else:
        for i, trait in enumerate(traits):
            name = trait.get("nome", "") if isinstance(trait, dict) else ""
            add(f"trait_{i+1}", sum(phrase(t, name) for t in readings.values()))
    spells = attrs.get("incantesimi_del_marchio") or {}
    if not isinstance(spells, dict) or not spells:
        add("spells_missing", 0)
    else:
        index = 0
        for values in spells.values():
            if not isinstance(values, list):
                add("invalid_spells", 0)
                continue
            for name in values:
                index += 1
                add(f"spell_{index}", sum(phrase(t, name) for t in readings.values()))
    return {
        "checks_total": len(checks),
        "checks_passed": sum(x["passed"] for x in checks.values()),
        "failed_check_ids": [k for k, v in checks.items() if not v["passed"]],
        "full_semantic_verification": False,
    }


def run(output):
    from supabase import create_client
    from scripts.import_manuals_from_r2 import _r2_client, _list_pdf_objects
    import pymupdf

    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("supabase_read_credentials_missing")
    db = create_client(url, key)
    rows = (db.table("private_reference_records")
            .select("id,source_key,reference_type,attributes,ai_review_status")
            .in_("id", list(IDS.values())).execute().data or [])
    records = {r["id"]: r for r in rows}
    if set(records) != set(IDS.values()):
        raise RuntimeError("target_record_missing")
    if any(r.get("source_key") != SOURCE or r.get("reference_type") != "subrace"
           for r in rows):
        raise RuntimeError("target_provenance_mismatch")

    r2 = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    obj = _list_pdf_objects(r2, bucket).get(SOURCE)
    if not obj or not 0 < obj["size"] < 600 * 1024 * 1024:
        raise RuntimeError("source_pdf_missing")
    results = []
    with tempfile.TemporaryDirectory(prefix="race-evidence-") as tmp:
        pdf_path = Path(tmp) / "source.pdf"
        r2.download_file(bucket, obj["key"], str(pdf_path))
        if sha256(pdf_path) != EXPECTED_SHA256:
            raise RuntimeError("source_sha_mismatch")
        with pymupdf.open(pdf_path) as pdf:
            if pdf.page_count != EXPECTED_PAGES:
                raise RuntimeError("source_page_count_mismatch")
            for page_number, (mark, parent) in TARGETS.items():
                page = pdf[page_number - 1]
                readings = {
                    "native": page.get_text("text", sort=True),
                    "psm4": ocr_text(page, Path(tmp), page_number, 4),
                    "psm11": ocr_text(page, Path(tmp), page_number, 11),
                }
                row = records[IDS[page_number]]
                item = compare(row, readings, mark)
                item.update({
                    "record_id": IDS[page_number],
                    "page": page_number,
                    "parent_match": fold((row.get("attributes") or {}).get(
                        "razza_genitore", "")) == fold(parent),
                    "ai_review_status_unchanged": row.get("ai_review_status"),
                })
                results.append(item)
    report = {
        "schema": "eberron-three-source-card-comparison-v1",
        "source_sha256_matched": True,
        "physical_pages_scanned": 3,
        "max_ocr_window": 12,
        "records": results,
        "lexical_pass": all(
            x["checks_passed"] == x["checks_total"] and x["parent_match"]
            for x in results
        ),
        "full_semantic_verification": False,
        "database_writes": 0,
    }
    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("EBERRON_THREE_COMPARISON " + json.dumps({
        "pages": 3, "failed_checks": [
            x["checks_total"] - x["checks_passed"] for x in results
        ], "lexical_pass": report["lexical_pass"], "database_writes": 0,
    }))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    run(parser.parse_args().output)
