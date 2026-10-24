#!/usr/bin/env python3
"""Identify source pages for Acquisitions and Wildemount playable races only.

No PDF text or image is uploaded. No Supabase connection or write. Each native
text batch is capped at 12 pages for clear provenance and bounded processing.
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

SOURCES = (
    {
        "file": "556883105-Acquisitions-Incorporated-D-D5e.pdf",
        "expected_sha256": "8066053a30443f5e4cd7e819e2aeff63d280af1ad0cbebc776d743cb3ee8b94d",
        "first": 65,
        "last": 84,
        "names": ("verdan",),
    },
    {
        "file": "469650052-Explorer-s-Guide-to-Wildemount-pdf.pdf",
        "first": 155,
        "last": 182,
        "names": ("pallid elf", "pallid elves", "lotusden halfling",
                  "lotusden", "draconblood", "ravenite", "orc of exandria"),
    },
)
PAGE_LIMIT = 12
LABELS = {
    "ability_scores": ("ability score increase", "ability score increases"),
    "size": ("size.", "size:"),
    "speed": ("speed.", "speed:"),
    "languages": ("languages.", "languages:"),
    "racial_traits": ("racial traits", "traits", "subrace"),
}


def page_facts(text: str, names: tuple[str, ...]) -> dict:
    """Metadata only; mentions cannot by themselves validate a playable race."""
    sample = (text or "").casefold()
    mentioned = [
        name for name in names
        if re.search(r"\b" + re.escape(name).replace(r"\ ", r"\s+") + r"\b", sample)
    ]
    return {
        "mentioned_race_keys": mentioned,
        "rule_markers": {k: any(v in sample for v in words) for k, words in LABELS.items()},
        "native_chars": len(sample),
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(path: Path, source: dict) -> dict:
    import pymupdf

    source_hash = _sha256(path)
    if source.get("expected_sha256") and source_hash != source["expected_sha256"]:
        raise ValueError("original_source_hash_mismatch")
    with pymupdf.open(path) as doc:
        result = []
        for start in range(source["first"], source["last"] + 1, PAGE_LIMIT):
            last = min(start + PAGE_LIMIT - 1, source["last"])
            assert 1 <= last - start + 1 <= PAGE_LIMIT
            for page_number in range(start, last + 1):
                if not 1 <= page_number <= doc.page_count:
                    break
                facts = page_facts(
                    doc[page_number - 1].get_text("text", sort=True),
                    source["names"],
                )
                if facts["mentioned_race_keys"] or facts["native_chars"] < 60:
                    result.append({"physical_page": page_number, **facts,
                                   "requires_manual_review": True})
        return {
            "source_filename": source["file"],
            "source_sha256": source_hash,
            "physical_page_count": doc.page_count,
            "native_pages_inspected": min(doc.page_count, source["last"]) - source["first"] + 1,
            "candidate_pages": result,
            "review_state": "source_candidates_not_verified",
            "database_writes": 0,
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    args = p.parse_args()
    for name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY"):
        os.environ.pop(name, None)
    from scripts.import_manuals_from_r2 import _list_pdf_objects, _r2_client

    client = _r2_client()
    bucket = os.getenv("R2_BUCKET", "tomoforge-manuals")
    objs = _list_pdf_objects(client, bucket)
    reports = []
    for source in SOURCES:
        item = objs.get(source["file"])
        if not item or not 0 < item["size"] < 600 * 1024 * 1024:
            reports.append({"source_filename": source["file"], "status": "missing_source"})
            continue
        try:
            with tempfile.TemporaryDirectory(prefix="species-native-") as tmp:
                original = Path(tmp) / "original.pdf"
                client.download_file(bucket, item["key"], str(original))
                reports.append(inspect(original, source))
        except Exception as exc:
            reports.append({
                "source_filename": source["file"],
                "status": "scan_error",
                "error_type": type(exc).__name__,
            })
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RACES_NATIVE_PAGE_DISCOVERY " + json.dumps([
        {"file": r["source_filename"],
         "pages": len(r.get("candidate_pages", [])),
         "status": r.get("status", "review_required")}
        for r in reports
    ]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
