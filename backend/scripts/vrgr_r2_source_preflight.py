"""Read-only, SHA-sealed inventory of Van Richten's private R2 source.

Only page-level text/structural marker counts are returned. No original book,
raw page text, OCR transcription, extracted personal data or secrets may enter
logs/artifacts. Source confirmation does NOT authorize canonical monster writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SOURCE_ID = "vrgr_2021_it"
FILENAME = "667440680-Guida-Di-Von-Richten-a-Ravenloft.pdf"
EXPECTED_SHA256 = "7d8e6479f592df1630fc3abb02d3612a1d8514b3faff8d558288005185980209"
EXPECTED_PAGES = 257
WRITES = 0

_MARKERS = ("classe armatura", "punti ferita", "velocità")
_ABILITY = ("for", "des", "cos", "int", "sag", "car")


def native_page_signals(text: str) -> dict[str, int | bool]:
    """Conservative page-level presence signals; not a statblock parser."""
    words = (text or "").casefold()
    markers = sum(marker in words for marker in _MARKERS)
    ability_count = sum(
        bool(re.search(rf"(?<!\w){abbr}(?!\w)", words)) for abbr in _ABILITY
    )
    return {
        "native_text_chars": len(text or ""),
        "structural_markers": markers,
        "ability_labels": ability_count,
        "monster_like_page": markers == 3 and ability_count == 6,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_local_pdf(path: Path) -> dict:
    """Fail closed on source identity, then summarize all physical pages."""
    if _sha256_file(path) != EXPECTED_SHA256:
        raise ValueError("registered_original_sha256_mismatch")
    import fitz

    with fitz.open(path) as document:
        if document.page_count != EXPECTED_PAGES:
            raise ValueError("registered_original_page_count_mismatch")
        rows = [
            {"page": number, **native_page_signals(document[number - 1].get_text("text"))}
            for number in range(1, EXPECTED_PAGES + 1)
        ]
    return {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "source_sha256_matched": True,
        "physical_pages_matched": True,
        "physical_pages": EXPECTED_PAGES,
        "pages_with_native_text": sum(row["native_text_chars"] >= 100 for row in rows),
        "pages_with_monster_like_native_text": [
            row["page"] for row in rows if row["monster_like_page"]
        ],
        "pages_with_armor_hp_speed_markers": [
            row["page"] for row in rows if row["structural_markers"] == 3
        ],
        "status": "read_only_page_signals_not_validated_statblocks",
        "database_writes": WRITES,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    # Local-only analysis without paid external AI.
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)
    from scripts import import_manuals_from_r2 as worker

    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals").strip()
    client = worker._r2_client()
    objects = worker._list_pdf_objects(client, bucket)
    obj = objects.get(FILENAME)
    if obj is None:
        raise RuntimeError("registered_van_richten_source_missing_in_r2")

    with tempfile.TemporaryDirectory(prefix="vrgr-source-preflight-") as temp:
        path = Path(temp) / FILENAME
        client.download_file(bucket, obj["key"], str(path))
        result = inspect_local_pdf(path)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("VRGR_SOURCE_PREFLIGHT " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
