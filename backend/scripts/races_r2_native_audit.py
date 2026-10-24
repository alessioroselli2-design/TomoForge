#!/usr/bin/env python3
"""Read-only, provenance-preserving native-text race coverage audit from R2.

Outputs only PDF filenames, source hashes, page numbers and candidate names.
Never prints, persists or uploads raw manual text, extracted feature prose,
PDF binaries, secrets, user ids, or OCR crops. Does not connect to Supabase.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from reference_library import _SOURCE_RACE_TITLES, parse_reference_page, text_is_usable

# Exact source keys already recorded in the owner's Supabase reference catalogue.
# Native-text scan only. A textless page is reported for an independent OCR pass.
SOURCES = (
    ("Guildmasters’ Guide to Ravnica.2 .pdf", "en", 72),
    ("953338587-Mythic-Odysseys-of-Theros.pdf", "en", 72),
    ("950799222-D-D-5e-Il-Tesoro-dei-Draghi-di-Fizban.pdf", "it", 72),
    ("682072052-5e-DnD-Dragonlance-Shadow-of-the-Dragon-Queen-Mong-IcYPD5.pdf", "en", 72),
    ("667440680-Guida-Di-Von-Richten-a-Ravenloft.pdf", "it", 72),
    ("779447314-Toaz-info-Strixhaven-a-Curriculum-of-Chaos-Dampd-5e-Pr-Ddb9ac0faaf75f03b8889d75914d10c4.pdf", "en", 72),
    ("556883105-Acquisitions-Incorporated-D-D5e.pdf", "en", 120),
    ("432286579-Locathah-Rising-5e.pdf", "en", 72),
)
MAX_WINDOW = 12
MAX_PDF_BYTES = 600 * 1024 * 1024


def page_candidates(text: str, source_filename: str, page: int, language: str) -> list[dict]:
    """Emit short identities from an actual structurally parsed page, not rules."""
    if not text_is_usable(text):
        return []
    results = parse_reference_page(text, source_filename, page, source_language=language)
    seen = set()
    out = []
    for record in results:
        name = str(record.get("name") or "")
        key = str(record.get("normalized_name") or "")
        if (
            record.get("reference_type") != "race"
            or "razza_sorgente_da_verificare" not in (record.get("review_flags") or [])
            or key not in _SOURCE_RACE_TITLES.get(source_filename.casefold(), ())
            or not 2 <= len(name) <= 84
            or key in seen
        ):
            continue
        seen.add(key)
        out.append({"name": name, "normalized_name": key, "page": page, "review_required": True})
    return out


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def scan_pdf(path: Path, source_filename: str, language: str, max_pages: int) -> dict:
    import pymupdf

    with pymupdf.open(path) as doc:
        total = doc.page_count
        limit = min(total, max_pages)
        candidates = []
        missing_text = []
        windows = []
        for start in range(1, limit + 1, MAX_WINDOW):
            stop = min(start + MAX_WINDOW - 1, limit)
            assert 1 <= stop - start + 1 <= MAX_WINDOW
            native_pages = 0
            for number in range(start, stop + 1):
                text = doc[number - 1].get_text("text") or ""
                if not text_is_usable(text):
                    missing_text.append(number)
                    continue
                native_pages += 1
                candidates.extend(page_candidates(text, source_filename, number, language))
            windows.append({"first_page": start, "last_page": stop, "native_text_pages": native_pages})
        return {
            "pdf_page_count": total,
            "scanned_page_count": limit,
            "window_count": len(windows),
            "windows": windows,
            "pages_requiring_ocr": missing_text,
            "candidate_names_and_pages": candidates,
            "candidate_count": len(candidates),
            "source_review_required": True,
            "status": "read_only_candidates_not_verified",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()
    if args.max_pages is not None and not 1 <= args.max_pages <= 120:
        raise ValueError("max_pages_must_be_between_1_and_120")

    # Prevent accidental hosted-LLM or database operations in this audit.
    for name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(name, None)

    from scripts import import_manuals_from_r2 as worker

    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals").strip()
    if not bucket:
        raise RuntimeError("missing_r2_bucket")
    client = worker._r2_client()
    objects = worker._list_pdf_objects(client, bucket)
    canonical = worker._importable_r2_objects(objects)

    result = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_native_text_no_ocr_no_database_writes",
        "max_ocr_pages_per_window": MAX_WINDOW,
        "sources": [],
        "database_writes": 0,
    }
    for name, language, default_limit in SOURCES:
        row = {"source_filename": name, "language": language}
        meta = canonical.get(name) or objects.get(name)
        if not meta:
            row["status"] = "source_not_found_in_r2"
            result["sources"].append(row)
            continue
        if meta["size"] <= 0 or meta["size"] > MAX_PDF_BYTES:
            row["status"] = "blocked_invalid_source_size"
            result["sources"].append(row)
            continue
        try:
            with tempfile.TemporaryDirectory(prefix="race-r2-native-audit-") as temp:
                file = Path(temp) / "source.pdf"
                client.download_file(bucket, meta["key"], str(file))
                row["sha256"] = _sha256(file)
                row.update(scan_pdf(
                    file,
                    name,
                    language,
                    min(args.max_pages or default_limit, default_limit),
                ))
        except Exception as exc:
            # Do not echo exception strings; they can contain paths or credentials.
            row["status"] = "source_scan_error"
            row["error_type"] = type(exc).__name__
        result["sources"].append(row)
        print(
            f"RACE_NATIVE_SCAN source={name} status={row['status']} "
            f"candidates={row.get('candidate_count', 0)}"
        )

    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RACE_NATIVE_AUDIT_SUMMARY " + json.dumps({
        "sources": len(result["sources"]),
        "candidates": sum(r.get("candidate_count", 0) for r in result["sources"]),
        "database_writes": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
