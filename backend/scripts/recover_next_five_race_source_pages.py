#!/usr/bin/env python3
"""Attach five more independently located original PDF pages to private race rows.

One physical page per race, double OCR, exact SHA and row fingerprint gates.
No text, images or PDF leave private R2/Supabase; no AI status is changed.
This is evidence recovery, NOT full semantic verification of race mechanics.
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

from scripts.recover_five_race_source_pages import (
    accepted, persist, sha256,
)

SOURCES = (
    {
        "filename": "950799222-D-D-5e-Il-Tesoro-dei-Draghi-di-Fizban.pdf",
        "sha": "f844e50d4c69ba2989bd7e221bbe70038e0a56f25cc3eada1825933ce0d4547a",
        "pages": 227,
        "targets": (
            ("ref_4b03252531500f471080590e5600e95a", "Dragonide Cromatico",
             "Dragonidi Cromatici", 11,
             ("Discendenza Cromatica", "Arma a Soffio", "Resistenza Draconica", "Protezione Cromatica")),
            ("ref_85c13f30bef25b5346c50147a88d3886", "Dragonide delle Gemme",
             "Dragonidi delle Gemme", 12,
             ("Discendenza Gemmata", "Arma a Soffio", "Resistenza Draconica", "Mente Psionica")),
            ("ref_16b5c2ef39db6dafa4f77e2dbe7fe53f", "Dragonide Metallico",
             "Dragonidi Metallici", 13,
             ("Discendenza Metallica", "Arma a Soffio", "Resistenza Draconica", "Soffio Metallico")),
        ),
    },
    {
        "filename": "667440680-Guida-Di-Von-Richten-a-Ravenloft.pdf",
        "sha": "7d8e6479f592df1630fc3abb02d3612a1d8514b3faff8d558288005185980209",
        "pages": 257,
        "targets": (
            ("ref_adfc52bfeb70792d74762001fd1ed6ae", "Dhampir", "Dhampir", 17,
             ("Eredità Ancestrale", "Arrampicata del Ragno", "Morso Vampirico", "Natura Senza Vita")),
            ("ref_80bec55e06ad78079eb6bd6c49fd02d4", "Rinato", "Rinato", 19,
             ("Eredità Ancestrale", "Natura Oltre la Morte", "Conoscenze di una Vita Passata")),
        ),
    },
)


def inspect_original(path: Path, config: dict) -> list[dict]:
    import pymupdf

    if sha256(path) != config["sha"]:
        raise RuntimeError("source_pdf_sha_mismatch")
    result = []
    with pymupdf.open(path) as pdf:
        if pdf.page_count != config["pages"]:
            raise RuntimeError("source_pdf_page_count_mismatch")
        with tempfile.TemporaryDirectory(prefix="private-five-next-pages-") as tmp:
            for target in config["targets"]:
                page = pdf[target[3] - 1]
                native = page.get_text("text", sort=True)
                # Both independent reads are required; OCR text is never logged.
                p4 = _ocr_italian(page, Path(tmp), target[3], 4)
                p6 = _ocr_italian(page, Path(tmp), target[3], 6)
                use_native = accepted(native, p4, target)
                chosen = native if use_native else p4
                corroboration = p4 if use_native else p6
                passed = accepted(chosen, corroboration, target)
                result.append({
                    "target": target,
                    "passed": passed,
                    "source": config["filename"],
                    "pdf_sha": config["sha"],
                    "source_text": chosen if passed else "",
                    "source_checksum": hashlib.sha256(chosen.encode()).hexdigest() if passed else "",
                    "second_mode": "psm4" if use_native else "psm6",
                })
    return result


def _ocr_italian(page, folder: Path, number: int, mode: int) -> str:
    import pymupdf
    import subprocess

    image = folder / f"race-{number}-{mode}.png"
    page.get_pixmap(matrix=pymupdf.Matrix(1.8, 1.8),
                    colorspace=pymupdf.csGRAY, alpha=False).save(image)
    try:
        proc = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", "ita+eng", "--psm", str(mode)],
            capture_output=True, text=True, check=False, timeout=80,
        )
        return proc.stdout if proc.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""
    finally:
        image.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(key, None)
    from scripts.import_manuals_from_r2 import _r2_client, _list_pdf_objects

    client = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    objects = _list_pdf_objects(client, bucket)
    rows = []
    with tempfile.TemporaryDirectory(prefix="private-race-source-") as tmp:
        for config in SOURCES:
            obj = objects.get(config["filename"])
            if not obj or not 0 < obj["size"] < 600 * 1024 * 1024:
                raise RuntimeError("registered_private_pdf_unavailable")
            path = Path(tmp) / config["filename"]
            client.download_file(bucket, obj["key"], str(path))
            rows.extend(inspect_original(path, config))
            path.unlink(missing_ok=True)
        outcomes = persist(rows, write=args.execute)

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({
        "schema": "five-more-private-source-pages-v1",
        "result": outcomes,
        "executed": args.execute,
        "ai_updates": 0,
        "source_text_emitted": False,
        "max_ocr_window_pages": 1,
    }, indent=2), encoding="utf-8")
    print("FIVE_MORE_PRIVATE_RACE_PAGES " + json.dumps({
        "executed": args.execute,
        "source_gates": sum(x["source_gate"] for x in outcomes),
        "restored": sum(x["result"] == "source_page_restored_ai_pending" for x in outcomes),
        "ai_updates": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
