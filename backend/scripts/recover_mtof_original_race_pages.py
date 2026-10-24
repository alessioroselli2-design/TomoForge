#!/usr/bin/env python3
"""Locate and attach private 2016 Mordenkainen 2018 race source pages by printed-page mapping.

No source text is exported in logs or Actions artifacts. PDFs stay ephemeral;
an OCR page is written only to the matching user's private record when the
original file hash, printed-page mapping, distinguishing original race features,
and unchanged database snapshot all agree. This never verifies rules or AI.
OCR runs in contiguous batches of at most 12 pages each.
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

SOURCE = "499493435-Mordenkainen-Tome-of-Foes completo .pdf"
HASH = "4a3ebff62306b82a1572eb00e98238d1171179d8eb2d8421c7b070ad1e3a013e"
EXPECTED_PAGES = 258
WINDOW_MAX = 12

# Original 2018 edition names and distinctive rule-feature labels, no rule prose.
TARGETS = (
    ("Tiefling di Baalzebul", 23, "Baalzebul", ("Legacy of Maladomini",)),
    ("Tiefling di Dispater", 23, "Dispater", ("Legacy of Dis",)),
    ("Tiefling di Fierna", 23, "Fierna", ("Legacy of Phlegethos",)),
    ("Tiefling di Glasya", 23, "Glasya", ("Legacy of Malbolge",)),
    ("Tiefling di Levistus", 23, "Levistus", ("Legacy of Stygia",)),
    ("Tiefling di Mammon", 23, "Mammon", ("Legacy of Minauros",)),
    ("Tiefling di Mephistopheles", 23, "Mephistopheles", ("Legacy of Cania",)),
    ("Tiefling di Zariel", 23, "Zariel", ("Legacy of Avernus",)),
    ("Eladrin (Mordenkainen 2018)", 61, "Eladrin", ("Fey Step", "Season")),
    ("Elfo del Mare (Mordenkainen 2018)", 62, "Sea Elf", ("Child of the Sea", "Sea Elf Training", "Friend of the Sea")),
    ("Shadar-kai (Mordenkainen 2018)", 62, "Shadar-kai", ("Blessing of the Raven Queen", "Necrotic Resistance")),
    ("Duergar (Mordenkainen 2018)", 81, "Duergar", ("Duergar Magic", "Sunlight Sensitivity", "Dwarven Resilience")),
    ("Gith", 96, "Gith", ("Gith Traits", "Ability Score Increase", "Languages")),
    ("Githyanki (Mordenkainen 2018)", 96, "Githyanki", ("Decadent Mastery", "Martial Prodigy", "Githyanki Psionics")),
    ("Githzerai (Mordenkainen 2018)", 97, "Githzerai", ("Mental Discipline", "Githzerai Psionics")),
    ("Gnomo delle Profondità (Mordenkainen 2018)", 113, "Deep Gnome", ("Stone Camouflage", "Superior Darkvision", "Svirfneblin")),
)


def norm(text: str) -> str:
    x = unicodedata.normalize("NFKD", (text or "").casefold())
    x = "".join(c for c in x if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", x.replace("’", "'").replace("‐", "-")).strip()


def page_score(raw: str, target: tuple) -> dict:
    txt = norm(raw)
    name = norm(target[2])
    heading = bool(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", txt))
    traits = tuple(k for k in target[3] if norm(k) in txt)
    enough = len(traits) >= (1 if len(target[3]) == 1 else 2)
    return {
        "name_detected": heading,
        "feature_count": len(traits),
        "features_required": 1 if len(target[3]) == 1 else 2,
        "sufficient": heading and enough and 650 <= len(raw) <= 25000,
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def ocr_page(page, temp: Path, n: int, psm: int) -> str:
    import pymupdf

    image = temp / f"p{n}-{psm}.png"
    page.get_pixmap(matrix=pymupdf.Matrix(1.9, 1.9),
                    colorspace=pymupdf.csGRAY, alpha=False).save(image)
    try:
        process = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", "eng", "--psm", str(psm)],
            text=True, capture_output=True, check=False, timeout=75,
        )
        return process.stdout if process.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""
    finally:
        image.unlink(missing_ok=True)


def scan(pdf_path: Path) -> list[dict]:
    import pymupdf

    if sha256(pdf_path) != HASH:
        raise RuntimeError("original_mtof_source_sha256_mismatch")
    results = []
    with pymupdf.open(pdf_path) as doc:
        if doc.page_count != EXPECTED_PAGES:
            raise RuntimeError("original_mtof_page_count_mismatch")
        physical_numbers = sorted({
            n for t in TARGETS
            for n in range(max(1, t[1] - 1), min(doc.page_count, t[1] + 4) + 1)
        })
        cache = {}
        with tempfile.TemporaryDirectory(prefix="mtof-2016-original-") as temp_dir:
            temp = Path(temp_dir)
            # Explicitly scoped OCR batches of <=12 physical pages each.
            for begin in range(0, len(physical_numbers), WINDOW_MAX):
                pages = physical_numbers[begin:begin + WINDOW_MAX]
                assert 1 <= len(pages) <= WINDOW_MAX
                for physical in pages:
                    page = doc[physical - 1]
                    text_native = page.get_text("text", sort=True)
                    p4 = ocr_page(page, temp, physical, 4)
                    p6 = ocr_page(page, temp, physical, 6)
                    cache[physical] = (text_native, p4, p6)
            for target in TARGETS:
                candidates = []
                for physical in range(max(1, target[1] - 1), min(doc.page_count, target[1] + 4) + 1):
                    native, p4, p6 = cache[physical]
                    readings = ((native, p4), (p4, p6))
                    for first, second in readings:
                        a, b = page_score(first, target), page_score(second, target)
                        if a["sufficient"] and b["sufficient"]:
                            candidates.append({
                                "physical": physical,
                                "first": first,
                                "score": min(a["feature_count"], b["feature_count"]),
                                "proof": "native+psm4" if first is native else "psm4+psm6",
                            })
                            break
                candidates.sort(key=lambda x: -x["score"])
                unique = bool(candidates and
                    (len(candidates) == 1 or candidates[0]["score"] > candidates[1]["score"]))
                best = candidates[0] if unique else None
                results.append({
                    "target": target,
                    "physical_page": best["physical"] if best else None,
                    "original_page_text": best["first"] if best else "",
                    "text_sha": hashlib.sha256(best["first"].encode()).hexdigest() if best else "",
                    "source_gate": bool(best),
                    "observed_candidates": len(candidates),
                    "reading_agreement": best["proof"] if best else "not_confirmed",
                })
    return results


def valid_row(row: dict, item: dict) -> bool:
    target = item["target"]
    return bool(
        row.get("name") == target[0] and row.get("source_key") == SOURCE
        and row.get("reference_type") in ("race", "subrace")
        and row.get("review_status") == "verified"
        and row.get("ai_review_status") == "pending"
        and not row.get("source_full_text") and not row.get("source_text_checksum")
        and any(isinstance(ref, dict) and ref.get("filename") == SOURCE
                and str(ref.get("page")) == str(target[1])
                for ref in (row.get("source_refs") or []))
    )


def persist(items: list[dict], write: bool) -> list[dict]:
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    token = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not token:
        raise RuntimeError("missing_supabase_read_credentials")
    client = create_client(url, token)
    summaries = []
    for item in items:
        name = item["target"][0]
        found = client.table("private_reference_records").select(
            "id,user_id,name,reference_type,source_key,review_status,ai_review_status,"
            "source_full_text,source_text_checksum,source_refs,attributes,review_notes"
        ).eq("source_key", SOURCE).eq("name", name).execute().data
        row = found[0] if found and len(found) == 1 else {}
        eligible = item["source_gate"] and valid_row(row, item)
        state = "source_or_snapshot_not_proven"
        if eligible:
            state = "safe_dry_run"
            if write:
                attrs = dict(row.get("attributes") or {})
                if "original_pdf_page_ocr_recovered" in attrs:
                    raise RuntimeError("source_recovery_duplicate")
                attrs["original_pdf_page_ocr_recovered"] = {
                    "physical_page": item["physical_page"],
                    "printed_page": item["target"][1],
                    "pdf_sha256": HASH,
                    "scope": "source-page-only_not_a_complete_rules_verification",
                    "reading_agreement": item["reading_agreement"],
                    "semantic_review_completed": False,
                }
                note = (str(row.get("review_notes") or "") +
                    "\nOriginal Mordenkainen 2018 source page restored privately; exact hash and "
                    "printed-vs-physical page relationship recorded. "
                    "No AI approval, original text not uploaded to GitHub.")
                payload = {
                    "source_full_text": item["original_page_text"],
                    "source_text_checksum": item["text_sha"],
                    "attributes": attrs,
                    "review_notes": note,
                }
                wrote = client.table("private_reference_records").update(payload).eq(
                    "id", row["id"]
                ).eq("user_id", row["user_id"]).eq("source_key", SOURCE).eq(
                    "source_text_checksum", ""
                ).eq("ai_review_status", "pending").execute().data
                if not wrote or len(wrote) != 1:
                    raise RuntimeError("mtof_private_source_update_failed")
                readback = client.table("private_reference_records").select(
                    "source_text_checksum,ai_review_status,review_status"
                ).eq("id", row["id"]).execute().data
                if (not readback or len(readback) != 1
                    or readback[0]["source_text_checksum"] != item["text_sha"]
                    or readback[0]["ai_review_status"] != "pending"
                    or readback[0]["review_status"] != "verified"):
                    raise RuntimeError("mtof_private_source_readback_failed")
                state = "source_restored_AI_pending"
        summaries.append({
            "name": name, "printed_page": item["target"][1],
            "physical_page_confirmed": item["physical_page"],
            "source_gate": item["source_gate"],
            "same_record_gate": bool(eligible), "result": state,
            "ambiguous_candidate_pages": item["observed_candidates"] if not item["source_gate"] else 0,
        })
    return summaries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    for n in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(n, None)
    from scripts.import_manuals_from_r2 import _list_pdf_objects, _r2_client
    r2 = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    item = _list_pdf_objects(r2, bucket).get(SOURCE)
    if not item or not 0 < item["size"] < 600 * 1024 * 1024:
        raise RuntimeError("mtof_original_source_missing")
    with tempfile.TemporaryDirectory(prefix="r2-mtof-legacy-") as folder:
        pdf = Path(folder) / SOURCE
        r2.download_file(bucket, item["key"], str(pdf))
        evidence = scan(pdf)
        results = persist(evidence, write=args.execute)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "schema": "mtof-races-private-page-recovery-v1",
        "targets": len(TARGETS), "database_writes_requested": args.execute,
        "ai_reviews_changed": 0, "ocr_max_pages_per_window": WINDOW_MAX,
        "outcomes": results,
    }, indent=2), encoding="utf-8")
    print("MTOF_PRIVATE_RACE_EVIDENCE " + json.dumps({
        "source_verified": True, "targets": len(results),
        "restored": sum(r["result"] == "source_restored_AI_pending" for r in results),
        "blocked": sum(not r["source_gate"] for r in results),
        "ai_reviews_changed": 0,
    }))


if __name__ == "__main__":
    main()
