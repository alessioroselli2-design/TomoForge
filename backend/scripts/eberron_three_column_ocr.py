#!/usr/bin/env python3
"""Read-only independent OCR checks for three split-column dragonmark pages.

Only normalized feature names, score pairs and evidence booleans are emitted.
No original rule prose, screenshots, or images are published. Each page is
a separate, 1-page OCR window (repository limit: at most 12 pages).
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
EXPECTED_SHA256 = "525e94622d502067d3e045f28e696759003cc360f2e7fd57364f13fc5b0731d5"
PAGE_COUNT = 322
TARGETS = {
    41: {
        "name": "Addestramento",
        "parent": "Umano",
        "feature_labels": ("Intuito Selvaggio", "Legame Primordiale",
                           "Più Grossi Sono", "Incantesimi del Marchio"),
        "terms": ("amicizia con gli animali", "parlare con gli animali",
                  "saggezza", "natura"),
    },
    43: {
        "name": "Guarigione",
        "parent": "Halfling",
        "feature_labels": ("Intuito Medico", "Tocco Guaritore",
                           "Incantesimi del Marchio"),
        "terms": ("cura ferite", "ristorare inferiore",
                  "saggezza", "medicina"),
    },
    51: {
        "name": "Sentinella",
        "parent": "Umano",
        "feature_labels": ("Intuito della Sentinella", "Scudo del Guardiano",
                           "Guardiano Vigile", "Incantesimi del Marchio"),
        "terms": ("costituzione", "saggezza", "scudo",
                  "reazione"),
    },
}
WINDOW_LIMIT = 12


def fold(text: str) -> str:
    raw = unicodedata.normalize("NFKD", (text or "").casefold())
    return re.sub(r"\s+", " ", "".join(
        ch for ch in raw if not unicodedata.combining(ch)
    )).strip()


def page_signals(text: str, profile: dict) -> dict:
    """Export only declared predicates, never input or OCR fragments."""
    observed = fold(text)
    name = fold(profile["name"])
    return {
        "heading": bool(re.search(r"\bmarchio\s+dell?[ao']?\s*" +
                                  re.escape(name) + r"\b", observed)),
        "score_heading": "incremento dei punteggi di caratteristica" in observed,
        "trait_labels_present": {
            label: fold(label) in observed for label in profile["feature_labels"]
        },
        "trait_terms_present": {
            term: fold(term) in observed for term in profile["terms"]
        },
        "characters": min(len(observed), 50000),
    }


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _ocr(page, scratch: Path, number: int, mode: int,
         crop: bool = False) -> str:
    import pymupdf

    fragments = []
    bounds = page.rect
    halves = (
        (pymupdf.Rect(bounds.x0, bounds.y0, bounds.x0 + bounds.width * 0.53, bounds.y1),
         pymupdf.Rect(bounds.x0 + bounds.width * 0.47, bounds.y0, bounds.x1, bounds.y1))
        if crop else (bounds,)
    )
    for col, rect in enumerate(halves):
        png = scratch / f"{number}-{mode}-{col}.png"
        page.get_pixmap(
            matrix=pymupdf.Matrix(2.0, 2.0),
            colorspace=pymupdf.csGRAY,
            alpha=False, clip=rect,
        ).save(png)
        try:
            proc = subprocess.run(
                ["tesseract", str(png), "stdout", "-l", "ita",
                 "--psm", str(mode)],
                capture_output=True, text=True, check=False, timeout=70,
            )
            fragments.append(proc.stdout if proc.returncode == 0 else "")
        except (subprocess.TimeoutExpired, OSError):
            fragments.append("")
        finally:
            png.unlink(missing_ok=True)
    return "\n".join(fragments)


def scan(path: Path) -> dict:
    import pymupdf

    if _hash(path) != EXPECTED_SHA256:
        raise ValueError("eberron_source_sha_mismatch")
    rows = []
    with pymupdf.open(path) as pdf:
        if pdf.page_count != PAGE_COUNT:
            raise ValueError("eberron_source_page_count_mismatch")
        with tempfile.TemporaryDirectory(prefix="eberron-column-") as folder:
            temp = Path(folder)
            for number, profile in TARGETS.items():
                page = pdf[number - 1]
                observations = {
                    "native": page_signals(page.get_text("text", sort=True), profile),
                    "psm4_full": page_signals(_ocr(page, temp, number, 4), profile),
                    "psm6_columns": page_signals(
                        _ocr(page, temp, number, 6, crop=True), profile
                    ),
                    "psm11_full": page_signals(_ocr(page, temp, number, 11), profile),
                }
                independent = (
                    observations["psm4_full"],
                    observations["psm6_columns"],
                    observations["psm11_full"],
                )
                labels = {
                    label: sum(
                        1 for run in independent
                        if run["trait_labels_present"][label]
                    )
                    for label in profile["feature_labels"]
                }
                terms = {
                    term: sum(
                        1 for run in independent
                        if run["trait_terms_present"][term]
                    )
                    for term in profile["terms"]
                }
                agreement = (
                    sum(bool(run["heading"]) for run in independent) >= 2
                    and sum(bool(run["score_heading"]) for run in independent) >= 2
                    and all(count >= 2 for count in labels.values())
                    and all(count >= 2 for count in terms.values())
                )
                rows.append({
                    "page": number,
                    "source_parent_from_registry": profile["parent"],
                    "source_race_key": profile["name"],
                    "observations": observations,
                    "label_ocr_votes": labels,
                    "term_ocr_votes": terms,
                    "two_mode_structural_agreement": agreement,
                    "status": "manual_rules_review_required",
                })
                print("DRAGONMARK_COLUMN_AUDIT " + json.dumps({
                    "page": number,
                    "two_mode_structural_agreement": agreement,
                    "labels_agree": sum(v >= 2 for v in labels.values()),
                    "labels_total": len(labels),
                }))
    return {
        "source": SOURCE,
        "source_hash_verified": True,
        "pages": rows,
        "window_size_each": 1,
        "max_window_limit": WINDOW_LIMIT,
        "database_writes": 0,
        "verified_record_writes": 0,
        "status": "read_only_source_candidates",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    for env in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
                "OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(env, None)

    from scripts.import_manuals_from_r2 import _list_pdf_objects, _r2_client

    client = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    item = _list_pdf_objects(client, bucket).get(SOURCE)
    if not item or not 0 < item["size"] < 600 * 1024 * 1024:
        raise RuntimeError("original_eberron_pdf_not_available")
    with tempfile.TemporaryDirectory(prefix="eberron-source-") as folder:
        original = Path(folder) / SOURCE
        client.download_file(bucket, item["key"], str(original))
        result = scan(original)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
