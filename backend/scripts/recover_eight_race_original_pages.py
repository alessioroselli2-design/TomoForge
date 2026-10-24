#!/usr/bin/env python3
"""Recover eight original race pages from multiple sealed private R2 manuals.

Source OCR is never included in GitHub artifacts or logs. The two OCR modes
must confirm the same race heading and at least two expected published traits.
The raw source is only a *page-level evidence attachment*. This script never
claims semantic verification and never changes AI or ordinary review statuses.
Each page uses its own one-page OCR window.
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

SOURCES = (
    {
        "filename": "368524312-The-Tortle-Package.pdf",
        "sha": "3dea9cd685343b1d90207b2b79f4a963cb3131f30e67f23d10795ace8f9f1a44",
        "pages": 28,
        "targets": (
            ("ref_9e6a2437f08c35d6a09a2593cf159461", "Tortle", "Tortle", 3,
             ("Shell Defense", "Natural Armor", "Claws")),
        ),
    },
    {
        "filename": "667440680-Guida-Di-Von-Richten-a-Ravenloft.pdf",
        "sha": "7d8e6479f592df1630fc3abb02d3612a1d8514b3faff8d558288005185980209",
        "pages": 257,
        "targets": (
            ("ref_80bec55e06ad78079eb6bd6c49fd02d4", "Rinato", "Rinato", 19,
             ("TRATTI", "Taglia", "Velocità", "Eredità ancestrale")),
            ("ref_ae70886af8935ba464598a36cdc42606", "Sangue Strigo", "Sangue Strigo", 21,
             ("TRATTI", "Taglia", "Velocità", "Eredità ancestrale")),
        ),
    },
    {
        "filename": "682072052-5e-DnD-Dragonlance-Shadow-of-the-Dragon-Queen-Mong-IcYPD5.pdf",
        "sha": "d867631c2344fbc8b1274478f01ad64e2f22989bf340b6b5ed8e001e63ce53a8",
        "pages": 227,
        "targets": (
            ("ref_258966c4a95e48d7cbfda8250fd484fd", "Kender", "Kender", 18,
             ("Fearless", "Kender Aptitude", "Taunt")),
        ),
    },
    {
        "filename": "779447314-Toaz-info-Strixhaven-a-Curriculum-of-Chaos-Dampd-5e-Pr-Ddb9ac0faaf75f03b8889d75914d10c4.pdf",
        "sha": "8f417ad08a68004869e141b1ab85e5659b95792250c8b82ddf70cb191f7c2063",
        "pages": 226,
        "targets": (
            ("ref_27adddc1690d5fecb3e74336df2369b2", "Owlin", "Owlin", 29,
             ("Flight", "Silent Feathers", "Darkvision")),
        ),
    },
    {
        "filename": "950799222-D-D-5e-Il-Tesoro-dei-Draghi-di-Fizban.pdf",
        "sha": "f844e50d4c69ba2989bd7e221bbe70038e0a56f25cc3eada1825933ce0d4547a",
        "pages": 227,
        "targets": (
            ("ref_4b03252531500f471080590e5600e95a", "Dragonide Cromatico", "Dragonide Cromatico", 11,
             ("Taglia", "Velocità", "Soffio")),
            ("ref_85c13f30bef25b5346c50147a88d3886", "Dragonide delle Gemme", "Gemme", 12,
             ("Taglia", "Velocità", "Soffio")),
            ("ref_16b5c2ef39db6dafa4f77e2dbe7fe53f", "Dragonide Metallico", "Dragonide Metallico", 13,
             ("Taglia", "Velocità", "Soffio")),
        ),
    },
)


def norm(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or "").casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", normalized).strip()


def check_text(text: str, target: tuple) -> dict:
    compact = norm(text)
    heading = norm(target[2])
    labels = [norm(k) in compact for k in target[4]]
    return {
        "heading": bool(re.search(r"(?<!\w)" + re.escape(heading) + r"(?!\w)", compact)),
        "feature_matches": sum(labels),
        "text_chars": len(text),
        "readable": 700 <= len(text) <= 15000,
    }


def accepted(primary: str, secondary: str, target: tuple) -> bool:
    a, b = check_text(primary, target), check_text(secondary, target)
    return bool(a["readable"] and b["readable"]
                and a["heading"] and b["heading"]
                and a["feature_matches"] >= 2
                and b["feature_matches"] >= 2)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for fragment in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(fragment)
    return digest.hexdigest()


def ocr(page, directory: Path, number: int, mode: int) -> str:
    import pymupdf

    image = directory / f"page-{number}-mode-{mode}.png"
    page.get_pixmap(
        matrix=pymupdf.Matrix(1.8, 1.8),
        colorspace=pymupdf.csGRAY, alpha=False,
    ).save(image)
    try:
        proc = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", "eng", "--psm", str(mode)],
            capture_output=True, text=True, check=False, timeout=80,
        )
        return proc.stdout if proc.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""
    finally:
        image.unlink(missing_ok=True)


def inspect_original(path: Path, config: dict) -> list[dict]:
    import pymupdf

    if sha256(path) != config["sha"]:
        raise RuntimeError("original_race_pdf_sha_mismatch")
    inspected = []
    with pymupdf.open(path) as pdf:
        if pdf.page_count != config["pages"]:
            raise RuntimeError("original_race_pdf_page_count_mismatch")
        candidates = {
            p for target in config["targets"]
            for p in range(max(1, target[3] - 2), min(pdf.page_count, target[3] + 2) + 1)
        }
        cached = {}
        with tempfile.TemporaryDirectory(prefix="eight-original-pages-") as tmp:
            # Batches bounded to at most 12 physical pages each.
            pages = sorted(candidates)
            for start in range(0, len(pages), 12):
                window = pages[start:start + 12]
                assert 1 <= len(window) <= 12
                for number in window:
                    page = pdf[number - 1]
                    cached[number] = (
                        page.get_text("text", sort=True),
                        ocr(page, Path(tmp), number, 4),
                        ocr(page, Path(tmp), number, 6),
                    )
            for target in config["targets"]:
                matches = []
                for number in range(max(1, target[3] - 2), min(pdf.page_count, target[3] + 2) + 1):
                    native, p4, p6 = cached[number]
                    if accepted(native, p4, target):
                        text, first, second = native, native, p4
                        proof = "native+psm4"
                    elif accepted(p4, p6, target):
                        text, first, second = p4, p4, p6
                        proof = "psm4+psm6"
                    else:
                        continue
                    features = min(
                        check_text(first, target)["feature_matches"],
                        check_text(second, target)["feature_matches"],
                    )
                    matches.append((features, number, text, proof))
                matches.sort(key=lambda x: -x[0])
                unique = bool(matches and (
                    len(matches) == 1 or matches[0][0] > matches[1][0]
                ))
                best = matches[0] if unique else None
                inspected.append({
                    "target": target,
                    "passed": bool(best),
                    "source": config["filename"],
                    "pdf_sha": config["sha"],
                    "physical_page": best[1] if best else None,
                    "source_text": best[2] if best else "",
                    "source_checksum": hashlib.sha256(best[2].encode()).hexdigest() if best else "",
                    "second_mode": best[3] if best else "unverified",
                    "matching_pages": len(matches),
                })
    return inspected


def valid_old_record(row: dict, evidence: dict) -> bool:
    target = evidence["target"]
    return bool(
        row.get("id") == target[0]
        and row.get("name") == target[1]
        and row.get("source_key") == evidence["source"]
        and row.get("reference_type") == "race"
        and row.get("review_status") == "verified"
        and row.get("ai_review_status") == "pending"
        and not row.get("source_full_text")
        and not row.get("source_text_checksum")
        and any(
            isinstance(ref, dict)
            and ref.get("filename") == evidence["source"]
            and str(ref.get("page")) == str(target[3])
            for ref in row.get("source_refs") or []
        )
    )


def persist(items: list[dict], *, write: bool) -> list[dict]:
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    secret = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not secret:
        raise RuntimeError("private_supabase_credentials_missing")
    client = create_client(url, secret)
    report = []
    for item in items:
        target = item["target"]
        found = (client.table("private_reference_records")
                 .select("id,user_id,name,source_key,reference_type,review_status,"
                         "ai_review_status,source_full_text,source_text_checksum,"
                         "source_refs,attributes,review_notes")
                 .eq("id", target[0]).execute().data)
        old = found[0] if found and len(found) == 1 else {}
        eligible = item["passed"] and valid_old_record(old, item)
        state = "source_not_confirmed_or_record_changed"
        if eligible:
            state = "safe_dry_run"
            if write:
                attrs = dict(old.get("attributes") or {})
                if "original_pdf_page_ocr_recovered" in attrs:
                    raise RuntimeError("source_recovery_already_recorded")
                attrs["original_pdf_page_ocr_recovered"] = {
                    "source_pdf_sha256": item["pdf_sha"],
                    "physical_page": item["physical_page"],
                    "registered_page": target[3],
                    "scope": "one_physical_source_page_not_approved_rule_block",
                    "method": "tesseract_psm4_psm6_or_native_psm4",
                    "semantic_review_completed": False,
                }
                comment = (
                    str(old.get("review_notes") or "") +
                    "\n2026-10-24: source page OCR restored from registered "
                    f"private R2 file, physical page {item['physical_page']}; dual reading "
                    "agreement; no rule or AI-status approval made."
                )
                payload = {
                    "source_full_text": item["source_text"],
                    "source_text_checksum": item["source_checksum"],
                    "attributes": attrs,
                    "review_notes": comment,
                }
                updated = (client.table("private_reference_records")
                           .update(payload)
                           .eq("id", target[0])
                           .eq("user_id", old["user_id"])
                           .eq("source_key", item["source"])
                           .eq("source_text_checksum", "")
                           .eq("ai_review_status", "pending")
                           .execute().data)
                if not updated or len(updated) != 1:
                    raise RuntimeError("fingerprinted_original_page_write_failed")
                after = (client.table("private_reference_records")
                         .select("source_text_checksum,ai_review_status,review_status")
                         .eq("id", target[0]).execute().data)
                if (not after or len(after) != 1
                        or after[0]["source_text_checksum"] != item["source_checksum"]
                        or after[0]["ai_review_status"] != "pending"
                        or after[0]["review_status"] != "verified"):
                    raise RuntimeError("private_original_page_readback_failed")
                state = "source_page_restored_ai_pending"
        report.append({
            "id": target[0], "name": target[1], "registered_page": target[3],
            "physical_page": item["physical_page"],
            "source_gate": item["passed"],
            "old_record_gate": bool(eligible),
            "result": state,
        })
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(name, None)
    from scripts.import_manuals_from_r2 import _r2_client, _list_pdf_objects

    r2 = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    objects = _list_pdf_objects(r2, bucket)
    inspected = []
    with tempfile.TemporaryDirectory(prefix="eight-r2-originals-") as tmp:
        for config in SOURCES:
            obj = objects.get(config["filename"])
            if not obj or not 0 < obj["size"] < 600 * 1024 * 1024:
                raise RuntimeError("required_registered_source_pdf_missing")
            local = Path(tmp) / config["filename"]
            r2.download_file(bucket, obj["key"], str(local))
            inspected.extend(inspect_original(local, config))
            local.unlink(missing_ok=True)
        results = persist(inspected, write=args.execute)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": "eight-private-race-source-pages-v1",
        "result": results,
        "executed": args.execute,
        "source_text_emitted": False,
        "ai_updates": 0,
        "ocr_max_window": 1,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("EIGHT_RACES_PRIVATE_SOURCE " + json.dumps({
        "executed": args.execute,
        "restored": sum(x["result"] == "source_page_restored_ai_pending" for x in results),
        "blocked": sum(not x["source_gate"] for x in results),
        "ai_updates": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
