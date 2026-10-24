#!/usr/bin/env python3
"""Evidence-only original PDF survey of Theros and Locathah playable species.

Each original R2 PDF is SHA-256 sealed; each scan has <=12 pages per source.
Two offline OCR modes independently report only allowlisted species names
and feature headings present/absent, never verbatim source text, images or
secrets. No Supabase access or network LLM calls.
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

SOURCES = (
    {
        "filename": "953338587-Mythic-Odysseys-of-Theros.pdf",
        "sha256": "0047c3322ca592c5833861a816d4404311c30165ecd4b4e70cc697de30d3a757",
        "pages": 262,
        "first": 17,
        "last": 28,
        "names": ("Centaur", "Leonin", "Minotaur", "Satyr", "Triton"),
    },
    {
        "filename": "432286579-Locathah-Rising-5e.pdf",
        "sha256": "8c2a0a17510fc84628534cd832ae171bade87460c6b22a48cc12b4fd48cd47a6",
        "pages": 39,
        "first": 21,
        "last": 27,
        "names": ("Locathah",),
    },
)
MARKERS = {
    "score_bonus": ("ability score increase",),
    "speed": ("speed.", "speed:"),
    "size": ("size.", "size:"),
    "languages": ("languages.", "languages:"),
    "darkvision": ("darkvision.", "darkvision:"),
    "skills": ("proficiency", "proficient"),
    "magical_resistance": ("magic resistance", "magical resistance"),
    "ambhibious": ("amphibious",),
    "natural_armor": ("natural armor", "natural armour"),
}
MAX_WINDOW = 12


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def structural_signals(text: str, names: tuple[str, ...]) -> dict:
    lowered = (text or "").casefold()
    lines = lowered.splitlines()
    mentions = [n for n in names if re.search(rf"\b{re.escape(n.casefold())}\b", lowered)]
    headings = [
        n for n in names
        if any(
            re.match(rf"^\s*{re.escape(n.casefold())}(?:\s+traits)?\s*(?:[:._-]|$)", line.strip())
            for line in lines
        )
    ]
    return {
        "mentions": mentions,
        "heading_candidates": headings,
        "markers": {key: any(word in lowered for word in markers) for key, markers in MARKERS.items()},
        "ocr_chars": min(len(text or ""), 40000),
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def run_tesseract(page, root: Path, mode: int) -> str:
    import pymupdf
    image = root / "sample.png"
    page.get_pixmap(
        matrix=pymupdf.Matrix(1.7, 1.7),
        colorspace=pymupdf.csGRAY,
        alpha=False,
    ).save(image)
    try:
        result = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", "eng", "--psm", str(mode)],
            capture_output=True, text=True, check=False, timeout=70,
        )
        return result.stdout if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""
    finally:
        image.unlink(missing_ok=True)


def inspect_pdf(path: Path, config: dict) -> dict:
    import pymupdf
    if sha256(path) != config["sha256"]:
        raise ValueError("source_sha256_mismatch")
    with pymupdf.open(path) as doc:
        if doc.page_count != config["pages"]:
            raise ValueError("source_page_count_mismatch")
        if config["last"] - config["first"] + 1 > MAX_WINDOW:
            raise ValueError("source_window_too_large")
        rows = []
        with tempfile.TemporaryDirectory(prefix="tomo-species-audit-") as temp:
            for n in range(config["first"], config["last"] + 1):
                page = doc[n - 1]
                a = structural_signals(run_tesseract(page, Path(temp), 4), config["names"])
                b = structural_signals(run_tesseract(page, Path(temp), 6), config["names"])
                agreed = sorted(set(a["heading_candidates"]) & set(b["heading_candidates"]))
                row = {
                    "physical_page": n,
                    "mode4": a,
                    "mode6": b,
                    "agreed_headings": agreed,
                    "source_review_required": True,
                }
                rows.append(row)
                print("SPECIES_PAGE " + json.dumps({
                    "filename":config["filename"],
                    "page":n,
                    "agreed_headings":agreed,
                    "structural_marker_count":sum(a["markers"].values()),
                }))
    return {
        "filename": config["filename"],
        "sha256_verified": True,
        "physical_pages": config["pages"],
        "scanned_start": config["first"],
        "scanned_end": config["last"],
        "rows": rows,
        "database_writes": 0,
        "status": "read_only_candidate_not_verified",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    for name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(name, None)
    from scripts.import_manuals_from_r2 import _list_pdf_objects, _r2_client

    client = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    objects = _list_pdf_objects(client, bucket)
    scans = []
    for cfg in SOURCES:
        meta = objects.get(cfg["filename"])
        if not meta or not 0 < meta["size"] < 600 * 1024 * 1024:
            scans.append({"filename": cfg["filename"], "status": "source_missing_or_invalid_size", "database_writes": 0})
            continue
        try:
            with tempfile.TemporaryDirectory(prefix="tomo-r2-species-") as tmp:
                pdf = Path(tmp) / cfg["filename"]
                client.download_file(bucket, meta["key"], str(pdf))
                scans.append(inspect_pdf(pdf, cfg))
        except Exception as exc:
            scans.append({"filename":cfg["filename"], "status":"source_scan_error", "error_type":type(exc).__name__,"database_writes":0})
    out = {"source_scans":scans,"database_writes":0,"note":"not source transcription or approved import"}
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
    print("SPECIES_AUDIT_SUMMARY "+json.dumps({
        "sources":len(scans),
        "statuses":[x["status"] for x in scans],
        "database_writes":0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
