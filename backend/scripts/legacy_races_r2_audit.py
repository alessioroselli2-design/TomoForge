#!/usr/bin/env python3
"""Locate 2014-legacy playable races in owner's original R2 PDFs, read-only.

No OCR text, images or source PDF files are ever written to the report.
Revisions to old source variants must be independently reviewed before import.
Each source is scoped to at most twelve physical PDF pages.
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
        "filename": "499493435-Mordenkainen-Tome-of-Foes completo .pdf",
        "start": 21, "end": 32,
        "names": (
            "Asmodeus", "Baalzebul", "Dispater", "Fierna", "Glasya",
            "Levistus", "Mammon", "Mephistopheles", "Zariel",
            "Eladrin", "Shadar-kai", "Sea Elf", "Duergar", "Gith",
        ),
    },
    {
        "filename": "616924846-Volo-s-Guide-to-Monsters.pdf",
        "start": 111, "end": 122,
        "names": (
            "Aasimar", "Firbolg", "Goliath", "Kenku", "Lizardfolk", "Tabaxi",
            "Triton", "Bugbear", "Goblin", "Hobgoblin", "Kobold",
            "Orc", "Yuan-ti",
        ),
    },
    {
        "filename": "368524312-The-Tortle-Package.pdf",
        "start": 2, "end": 7,
        "names": ("Tortle", "Tortles"),
    },
)
WINDOW_MAX = 12
STRUCTURE_MARKERS = (
    "ability score increase", "speed.", "languages.", "size.",
    "racial traits", "subrace", "legacy of", "infernal legacy",
    "incremento dei punteggi", "velocità.", "tratti razziali",
)


def short_evidence(text: str, allowed_names: tuple[str, ...]) -> dict:
    content = (text or "").casefold()
    words = []
    for race in allowed_names:
        escaped = re.escape(race.casefold()).replace(r"\ ", r"\s+")
        if re.search(r"\b" + escaped + r"\b", content):
            words.append(race)
    return {
        "candidate_mentions": words,
        "number_of_rule_anchors": sum(marker in content for marker in STRUCTURE_MARKERS),
        "native_or_ocr_text_present": len(content) >= 75,
    }


def _sha256(pdf: Path) -> str:
    h = hashlib.sha256()
    with pdf.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ocr(page, working_dir: Path, mode: int) -> str:
    import pymupdf

    path = working_dir / "page.png"
    page.get_pixmap(
        matrix=pymupdf.Matrix(1.6, 1.6), colorspace=pymupdf.csGRAY,
        alpha=False,
    ).save(path)
    try:
        result = subprocess.run(
            ["tesseract", str(path), "stdout", "-l", "eng", "--psm", str(mode)],
            check=False, text=True, capture_output=True, timeout=60,
        )
        return result.stdout if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""
    finally:
        path.unlink(missing_ok=True)


def scan(pdf: Path, config: dict) -> dict:
    import pymupdf

    assert 0 < config["end"] - config["start"] + 1 <= WINDOW_MAX
    with pymupdf.open(pdf) as doc:
        total_pages = doc.page_count
        actual_scanned = max(0, min(doc.page_count, config["end"]) - config["start"] + 1)
        windows = []
        with tempfile.TemporaryDirectory(prefix="legacy-races-") as tmp:
            for physical in range(config["start"], config["end"] + 1):
                if physical > doc.page_count:
                    break
                page = doc[physical - 1]
                native = short_evidence(page.get_text("text", sort=True), config["names"])
                if native["candidate_mentions"] and native["number_of_rule_anchors"] >= 2:
                    observations = {"native": native}
                else:
                    observations = {
                        "native": native,
                        "psm4": short_evidence(_ocr(page, Path(tmp), 4), config["names"]),
                        "psm6": short_evidence(_ocr(page, Path(tmp), 6), config["names"]),
                    }
                if any(o["candidate_mentions"] for o in observations.values()):
                    windows.append({
                        "physical_page": physical,
                        "observations": observations,
                        "status": "source_candidate_needs_rule_review",
                    })
    return {
        "source": config["filename"],
        "sha256": _sha256(pdf),
        "pdf_page_count": total_pages,
        "pages_inspected": actual_scanned,
        "candidate_pages": windows,
        "mode": "read_only_no_db_access",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    for env in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY"):
        os.environ.pop(env, None)
    from scripts.import_manuals_from_r2 import _list_pdf_objects, _r2_client

    client = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    objects = _list_pdf_objects(client, bucket)
    rows = []
    for config in SOURCES:
        src = objects.get(config["filename"])
        if not src or not 0 < src["size"] < 600 * 1024 * 1024:
            rows.append({"source": config["filename"], "status": "not_found_in_R2"})
            continue
        try:
            with tempfile.TemporaryDirectory(prefix="legacy-owned-r2-") as tmp:
                path = Path(tmp) / "original.pdf"
                client.download_file(bucket, src["key"], str(path))
                rows.append(scan(path, config))
        except Exception as exc:
            rows.append({"source": config["filename"], "status": "scan_failure",
                         "error_type": type(exc).__name__})
    outfile = Path(args.output)
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text(json.dumps({"sources": rows,"database_writes": 0}, indent=2),
                       encoding="utf-8")
    print("LEGACY_RACES " + json.dumps([
        {"source": row["source"],
         "candidate_pages": len(row.get("candidate_pages", [])),
         "status": row.get("status", "needs_review")} for row in rows
    ]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
