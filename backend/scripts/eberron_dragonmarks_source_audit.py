#!/usr/bin/env python3
"""Isolated, read-only Eberron dragonmark source-quality audit, pages 41–52.

The output is *only* page indexes, cryptographic source identity and structural
marker agreement. Never write source paragraphs, screenshots or OCR to the repo,
workflow log, downloadable artifact or Supabase.
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

SOURCE = "618795464-Eberron.pdf"
EXPECTED_PAGES = 322
FIRST = 41
LAST = 52
TARGETS = {
    41: "Addestramento",
    42: "Costruzione",
    43: "Guarigione",
    44: "Individuazione",
    45: "Interdizione",
    46: "Ombra",
    47: "Ospitalità",
    48: "Passaggio",
    49: "Scoperta",
    50: "Scrittura",
    51: "Sentinella",
    52: "Tempesta",
}
# These pages were found truncated or materially OCR-corrupted in stored records.
REVIEW_PAGES = frozenset({41, 43, 44, 45, 47, 50, 51, 52})
SCHEMA_VERSION = "eberron-dragonmark-source-quality-v1"


def _fold(value: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def page_markers(text: str, expected: str) -> dict:
    """Booleans only: no source prose, missing core values or invented repairs."""
    sample = _fold(text or "")
    return {
        "named_heading_seen": bool(re.search(r"marchio\s+dell?[ao']?\s*" + re.escape(_fold(expected)) + r"\b", sample)),
        "race_parent_context": bool(re.search(
            r"\b(personaggio\s+(?:umano|nano|elfo|halfling|mezzelfo|mezzorco|gnomo)|appartiene\s+a\s+questa\s+sottorazza)\b",
            sample,
        )),
        "ability_increase_heading": "incremento dei punteggi di caratteristica" in sample,
        "spell_table_reference": "incantesimi del marchio" in sample,
        "at_least_one_feature_label": any(label in sample for label in (
            "intuito", "intuitivo", "magico", "magia", "guardiano", "sentinella",
            "saggezza", "ombra", "abilità", "abilita",
        )),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ocr(image: Path, mode: int) -> str:
    try:
        result = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", "ita", "--psm", str(mode)],
            capture_output=True, text=True, timeout=45, check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def review_page(number: int, native: str, page, root: Path) -> dict:
    expected = TARGETS[number]
    native_markers = page_markers(native, expected)
    data = {
        "page": number,
        "dragonmark": expected,
        "native_text_chars": len(native),
        "native": native_markers,
        "needs_ocr_comparison": number in REVIEW_PAGES,
    }
    if number not in REVIEW_PAGES:
        return data
    import pymupdf

    image = root / f"page_{number}.png"
    page.get_pixmap(
        matrix=pymupdf.Matrix(1.8, 1.8),
        colorspace=pymupdf.csGRAY,
        alpha=False,
    ).save(image)
    try:
        one = page_markers(_ocr(image, 4), expected)
        two = page_markers(_ocr(image, 6), expected)
    finally:
        image.unlink(missing_ok=True)
    data["ocr_psm4"] = one
    data["ocr_psm6"] = two
    data["agreement"] = {
        field: one[field] and two[field]
        for field in one
    }
    data["manual_review_required"] = True
    return data


def audit(pdf: Path) -> dict:
    import pymupdf

    with pymupdf.open(pdf) as document:
        if document.page_count != EXPECTED_PAGES:
            raise ValueError("eberron_page_count_does_not_match_registered_source")
        with tempfile.TemporaryDirectory(prefix="eberron-dragonmarks-") as tmp:
            pages = [
                review_page(
                    index,
                    document[index - 1].get_text("text", sort=True),
                    document[index - 1],
                    Path(tmp),
                )
                for index in range(FIRST, LAST + 1)
            ]
    return {
        "schema": SCHEMA_VERSION,
        "source_filename": SOURCE,
        "source_sha256": _sha256(pdf),
        "physical_pages": EXPECTED_PAGES,
        "first_page": FIRST,
        "last_page": LAST,
        "pages_scanned": len(pages),
        "max_source_window": LAST - FIRST + 1,
        "pages": pages,
        "status": "read_only_source_quality_no_verification",
        "database_writes": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        os.environ.pop(key, None)

    from scripts.import_manuals_from_r2 import _list_pdf_objects, _r2_client

    client = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    entry = _list_pdf_objects(client, bucket).get(SOURCE)
    if not entry or not 0 < entry["size"] <= 600 * 1024 * 1024:
        raise RuntimeError("registered_eberron_pdf_missing_or_invalid_size")

    with tempfile.TemporaryDirectory(prefix="eberron-original-") as tmp:
        pdf = Path(tmp) / SOURCE
        client.download_file(bucket, entry["key"], str(pdf))
        result = audit(pdf)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("EBERRON_SOURCE_QUALITY " + json.dumps({
        "sha256": result["source_sha256"],
        "pages_scanned": result["pages_scanned"],
        "ocr_pages": len(REVIEW_PAGES),
        "two_mode_heading_agreement": [
            item["page"] for item in result["pages"]
            if item.get("agreement", {}).get("named_heading_seen")
        ],
        "db_writes": result["database_writes"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
