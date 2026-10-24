#!/usr/bin/env python3
"""Read-only factual recovery for three fragmented Eberron dragonmark records.

The output contains only page numbers, score/delta pairs, compact trait titles,
text-quality indicators and agreement metadata. Original copyrighted page text
and OCR transcriptions must NEVER be written to logs, artifacts or the repo.
The script cannot mark a record verified and never connects to Supabase.
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
EXPECTED_PAGES = 322
TARGETS = {
    41: ("Addestramento", "Umano"),
    43: ("Guarigione", "Halfling"),
    51: ("Sentinella", "Umano"),
}
SCORES = ("forza", "destrezza", "costituzione", "intelligenza", "saggezza", "carisma")
MAX_TEXT_CHARS = 20000


def fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", normalized).strip()


def factual_signals(text: str, mark: str) -> dict:
    """Return only bounded, factual categories; never source paragraph text."""
    raw = (text or "")[:MAX_TEXT_CHARS]
    compact = fold(raw)
    mark_seen = bool(re.search(
        rf"marchio\s+dell?[ao']?\s*{re.escape(fold(mark))}\b",
        compact,
    ))
    stat_matches: list[dict] = []
    # Captures explicit printed increases, not guessed or inferred scores.
    patt = (
        r"(?:punteggio\s+di|quello\s+di)\s+"
        r"(forza|destrezza|costituzione|intelligenza|saggezza|carisma)"
        r"(?:\s+del\s+personaggio)?\s+aumenta\s+di\s+(\d{1,2})\b"
    )
    for m in re.finditer(patt, compact):
        score, delta = m.groups()
        if score not in SCORES or int(delta) not in (1, 2):
            continue
        pair = {"stat": score, "increase": int(delta)}
        if pair not in stat_matches:
            stat_matches.append(pair)
    # Printed trait labels only: short, bounded, anchored to a title followed
    # by a sentence. No mechanical rules or text passages are exported.
    candidates: list[str] = []
    for m in re.finditer(
        r"(?m)^\s*([A-ZÀÈÌÒÙ][A-Za-zÀ-ÿ'’ -]{2,49})\.\s*"
        r"(?=(?:Quando|Il|La|L'|Un|Una|Può|A partire|Se|Questo|Questa|Ogni)\b)",
        raw,
    ):
        title = " ".join(m.group(1).split()).strip()
        if len(title.split()) > 6 or len(title) > 52:
            continue
        if title.casefold() not in {v.casefold() for v in candidates}:
            candidates.append(title)
    return {
        "named_heading_seen": mark_seen,
        "ability_increase_heading_seen": "incremento dei punteggi di caratteristica" in compact,
        "spell_mark_heading_seen": "incantesimi del marchio" in compact,
        "explicit_score_increases": stat_matches[:6],
        "short_printed_trait_labels": candidates[:15],
        "text_usable": len(compact) >= 250,
    }


def ocr_text(page, directory: Path, page_number: int, mode: int) -> str:
    import pymupdf
    image = directory / f"page-{page_number}.png"
    page.get_pixmap(matrix=pymupdf.Matrix(1.7, 1.7), colorspace=pymupdf.csGRAY, alpha=False).save(image)
    try:
        result = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", "ita", "--psm", str(mode)],
            text=True, capture_output=True, check=False, timeout=75,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    finally:
        image.unlink(missing_ok=True)
    return result.stdout if result.returncode == 0 else ""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_pdf(path: Path) -> dict:
    import pymupdf

    if sha256(path) != EXPECTED_SHA256:
        raise ValueError("original_eberron_source_hash_mismatch")
    with pymupdf.open(path) as doc:
        if doc.page_count != EXPECTED_PAGES:
            raise ValueError("original_eberron_page_count_mismatch")
        items = []
        with tempfile.TemporaryDirectory(prefix="eberron-traits-") as tmp:
            for number, (name, race) in TARGETS.items():
                page = doc[number - 1]
                observations = {
                    "native": factual_signals(page.get_text("text", sort=True), name),
                    "psm4": factual_signals(ocr_text(page, Path(tmp), number, 4), name),
                    "psm6": factual_signals(ocr_text(page, Path(tmp), number, 6), name),
                }
                groups = list(observations.values())
                confirmed = [
                    pair for pair in groups[0]["explicit_score_increases"]
                    if all(pair in other["explicit_score_increases"] for other in groups[1:])
                ]
                all_headings = all(o["named_heading_seen"] for o in groups)
                items.append({
                    "page": number,
                    "name": "Marchio " + ("dell'" if name in ("Addestramento",) else "della " if name in ("Guarigione", "Sentinella") else "di ") + name,
                    "race_parent_from_existing_database": race,
                    "observations": observations,
                    "independent_heading_agreement": all_headings,
                    "explicit_score_three_way_agreement": confirmed,
                    "needs_manual_review_before_write": True,
                })
                print("EBERRON_MARK_PAGE " + json.dumps({
                    "page": number,
                    "heading_confirmed": all_headings,
                    "score_pairs_agreed": len(confirmed),
                }))
    return {
        "status": "factual_source_candidates_only_not_verified",
        "filename": SOURCE,
        "sha256_matched": True,
        "pages_processed": sorted(TARGETS),
        "items": items,
        "database_writes": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    for key in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(key, None)
    from scripts.import_manuals_from_r2 import _list_pdf_objects, _r2_client

    client = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    obj = _list_pdf_objects(client, bucket).get(SOURCE)
    if obj is None or not 0 < obj["size"] < 600 * 1024 * 1024:
        raise RuntimeError("original_eberron_source_missing_or_invalid_size")
    with tempfile.TemporaryDirectory(prefix="eberron-three-original-") as tmp:
        path = Path(tmp) / SOURCE
        client.download_file(bucket, obj["key"], str(path))
        result = inspect_pdf(path)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("EBERRON_RECOVERY " + json.dumps({
        "pages": result["pages_processed"],
        "database_writes": 0,
        "source_identity_verified": result["sha256_matched"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
