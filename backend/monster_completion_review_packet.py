"""Produce a source-review handoff without claiming independent approval.

This tool intentionally cannot set independent_review or ai_verified.
A separate reviewer/process must return an evidence-bound verdict.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from monster_completion_preflight import preflight
from translation_integrity import translation_verification_fingerprint


def build_review_packet(original: dict, candidate: dict) -> dict:
    check = preflight(original, candidate, source_page_checked=False,
                      source_sections_checked=False, independent_review=False)
    refs = original.get("source_refs") or []
    if not isinstance(refs, list):
        refs = []
    return {
        "schema": "tomoforge.monster.source_review_request.v1",
        "record_id": original.get("id"),
        "source_name": original.get("source_name"),
        "source_refs": refs,
        "candidate_fingerprint": translation_verification_fingerprint(candidate),
        "candidate_name": candidate.get("name"),
        "handoff_ready": not any(b for b in check.blockers if b not in {
            "source_page_not_checked", "source_sections_not_checked",
            "independent_review_missing"}),
        "source_review_tasks": [
            "Check every original descriptive paragraph against the Italian candidate",
            "Compare every stat value, dice expression, damage type, save DC, and condition",
            "Check traits, actions, bonus actions, reactions, and legendary actions, including absent sections",
            "Check spell names and casting frequencies against the original source",
            "Verify conversions from feet to meters and detect omissions",
        ],
        "structural_blockers": [
            b for b in check.blockers
            if b not in {"source_page_not_checked", "source_sections_not_checked",
                         "independent_review_missing"}
        ],
        "reviewer_verdict": None,
        "reviewer_identity": None,
        "review_evidence": None,
        "independent_review": False,
        "approved": False,
        "writes_performed": 0,
        "instructions": "Return a separately sourced, independently produced verdict. "
                        "This packet is a request, never an approval.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    original = json.loads(args.original.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    print(json.dumps(build_review_packet(original, candidate), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
