#!/usr/bin/env python3
"""Recover five exact-source playable-race PDF pages into private Supabase.

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
        "filename": "953338587-Mythic-Odysseys-of-Theros.pdf",
        "sha": "0047c3322ca592c5833861a816d4404311c30165ecd4b4e70cc697de30d3a757",
        "pages": 262,
        "targets": (
            ("ref_dad678437818ee106cede7652e8dda48", "Leonin", "Leonin", 22,
             ("Daunting Roar", "Hunter's Instincts", "Claws", "Darkvision")),
            ("ref_d4182b9ec03b4a5578e264b449cb6c66", "Satiro", "Satyr", 26,
             ("Magic Resistance", "Mirthful Leaps", "Reveler", "Ram")),
        ),
    },
    {
        "filename": "432286579-Locathah-Rising-5e.pdf",
        "sha": "8c2a0a17510fc84628534cd832ae171bade87460c6b22a48cc12b4fd48cd47a6",
        "pages": 39,
        "targets": (
            ("ref_46d214686cc045d4ed45a7afee6f482c", "Locathah", "Locathah", 24,
             ("Limited Amphibiousness", "Leviathan Will",
              "Natural Armor", "Observant and Athletic")),
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
        "filename": "556883105-Acquisitions-Incorporated-D-D5e.pdf",
        "sha": "8066053a30443f5e4cd7e819e2aeff63d280af1ad0cbebc776d743cb3ee8b94d",
        "pages": 226,
        "targets": (
            ("ref_52c72666e26647e11d491419dc598655", "Verdan", "Verdan", 75,
             ("Black Blood Healing", "Limited Telepathy",
              "Persuasive", "Telepathic Insight")),
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
        raise RuntimeError("registered_source_pdf_sha_mismatch")
    inspected = []
    with pymupdf.open(path) as pdf:
        if pdf.page_count != config["pages"]:
            raise RuntimeError("registered_source_pdf_page_count_mismatch")
        with tempfile.TemporaryDirectory(prefix="five-original-pages-") as tmp:
            for target in config["targets"]:
                page = pdf[target[3] - 1]
                p4 = ocr(page, Path(tmp), target[3], 4)
                p6 = ocr(page, Path(tmp), target[3], 6)
                native = page.get_text("text", sort=True)
                chosen = native if accepted(native, p4, target) else p4
                second = p4 if chosen is native else p6
                passes = accepted(chosen, second, target)
                inspected.append({
                    "target": target,
                    "passed": passes,
                    "source": config["filename"],
                    "pdf_sha": config["sha"],
                    "source_text": chosen if passes else "",
                    "source_checksum": hashlib.sha256(chosen.encode()).hexdigest()
                    if passes else "",
                    "second_mode": "psm4" if chosen is native else "psm6",
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
                    "physical_page": target[3],
                    "scope": "one_physical_source_page_not_approved_rule_block",
                    "method": "tesseract_psm4_psm6_or_native_psm4",
                    "semantic_review_completed": False,
                }
                comment = (
                    str(old.get("review_notes") or "") +
                    "\n2026-10-24: source page OCR restored from registered "
                    f"private R2 file, physical page {target[3]}; dual reading "
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
            "id": target[0], "name": target[1], "page": target[3],
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
    with tempfile.TemporaryDirectory(prefix="five-r2-originals-") as tmp:
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
        "schema": "five-private-source-pages-v1",
        "result": results,
        "executed": args.execute,
        "source_text_emitted": False,
        "ai_updates": 0,
        "ocr_max_window": 1,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FIVE_RACES_PRIVATE_SOURCE " + json.dumps({
        "executed": args.execute,
        "restored": sum(x["result"] == "source_page_restored_ai_pending" for x in results),
        "blocked": sum(not x["source_gate"] for x in results),
        "ai_updates": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
