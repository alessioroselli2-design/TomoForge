#!/usr/bin/env python3
"""Read-only scoped OCR survey for Theros playable race options.

Only short predeclared race names, page numbers and structural booleans are
emitted. The R2 PDF is an owner-provided official supplement; metadata is never sufficient for
VERIFIED data; no private OCR prose, scans, credentials or DB rows are emitted.
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
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SOURCE = "953338587-Mythic-Odysseys-of-Theros.pdf"
EXPECTED_SHA256 = "0047c3322ca592c5833861a816d4404311c30165ecd4b4e70cc697de30d3a757"
EXPECTED_PAGES = 262
FIRST, LAST = 19, 36
NAMES = ("Centaur", "Leonin", "Minotaur", "Satyr", "Triton")
STRUCTURAL = {
    "score_bonus": ("ability score increase", "ability score increases"),
    "size": ("size.", "size:"),
    "speed": ("speed.", "speed:"),
    "languages": ("languages.", "languages:"),
    "creature_type": ("creature type.", "creature type:"),
    "racial_traits": ("traits", "racial traits"),
    "subspecies": ("roar", "claws", "ram", "magic resistance", "mirthful leaps", "amphibious"),
}


def facts(text: str) -> dict:
    text = (text or "").casefold()
    lines = text.splitlines()
    race_headings = []
    race_mentions = []
    for name in NAMES:
        base = name.casefold()
        escaped = re.escape(base).replace(r"\ ", r"\s+")
        if re.search(rf"\b{escaped}\b", text):
            race_mentions.append(name)
        if any(re.match(rf"^\s*{escaped}\s*(?:traits|\b|[.:_])", line) for line in lines):
            race_headings.append(name)
    return {
        "name_mentions": race_mentions,
        "possible_headings": race_headings,
        "structural_markers": {
            key: any(t in text for t in phrases)
            for key, phrases in STRUCTURAL.items()
        },
        "text_chars": min(len(text), 100000),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ocr(page, folder: Path, number: int, mode: int) -> str:
    import pymupdf
    image = folder / f"theros-p{number}.png"
    page.get_pixmap(
        matrix=pymupdf.Matrix(1.7, 1.7),
        colorspace=pymupdf.csGRAY, alpha=False,
    ).save(image)
    try:
        p = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", "eng", "--psm", str(mode)],
            capture_output=True, text=True, timeout=75, check=False,
        )
        return p.stdout if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""
    finally:
        image.unlink(missing_ok=True)


def scan(pdf: Path) -> dict:
    import pymupdf
    if sha256(pdf) != EXPECTED_SHA256:
        raise ValueError("source_sha_mismatch")
    with pymupdf.open(pdf) as doc:
        if doc.page_count != EXPECTED_PAGES:
            raise ValueError("source_page_count_mismatch")
        pages = []
        with tempfile.TemporaryDirectory(prefix="theros-ocr-") as tmp:
            # Explicitly bounded batches: a maximum of 12 pages per window.
            windows = []
            for start in range(FIRST, LAST + 1, 12):
                stop = min(start + 11, LAST)
                assert 1 <= stop - start + 1 <= 12
                windows.append({"first": start, "last": stop})
                for number in range(start, stop + 1):
                    page = doc[number - 1]
                    a = facts(ocr(page, Path(tmp), number, 4))
                    b = facts(ocr(page, Path(tmp), number, 6))
                    common = sorted(set(a["possible_headings"]) & set(b["possible_headings"]))
                    pages.append({
                        "page": number,
                        "psm4": a,
                        "psm6": b,
                        "agreed_heading_candidates": common,
                        "manual_review_required": True,
                    })
                    print("THEROS_SOURCE_PAGE " + json.dumps({
                        "page": number,
                        "agreed_heading_candidates": common,
                        "ocr_passes_nonempty": int(a["text_chars"] > 100) + int(b["text_chars"] > 100),
                    }))
    return {
        "filename": SOURCE,
        "source_sha_verified": True,
        "source_role": "official_supplement_not_self_verifying",
        "logical_source_id": "mot_2020_en",
        "pages": pages,
        "window_first": FIRST,
        "window_last": LAST,
        "windows": windows,
        "max_window_size": 12,
        "mode": "read_only_source_candidate_not_verified",
        "database_writes": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    for key in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(key, None)
    from scripts.import_manuals_from_r2 import _r2_client, _list_pdf_objects
    client = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    obj = _list_pdf_objects(client, bucket).get(SOURCE)
    if not obj or not 0 < obj["size"] < 600 * 1024 * 1024:
        raise RuntimeError("registered_theros_source_unavailable")
    with tempfile.TemporaryDirectory(prefix="theros-r2-source-") as tmp:
        path = Path(tmp) / SOURCE
        client.download_file(bucket, obj["key"], str(path))
        result = scan(path)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("THEROS_SOURCE_SUMMARY " + json.dumps({
        "pages": len(result["pages"]),
        "source_verified": result["source_sha_verified"],
        "database_writes": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
