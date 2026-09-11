#!/usr/bin/env python3
"""Conservative, read-only parser-readiness gate for OCR text.

This helper evaluates whether OCR output contains enough stable D&D stat-block
structure to justify a later bounded parser pilot. It never writes Supabase,
creates canonical records, repairs OCR text, or authorizes automatic import.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any

PARSER_CANDIDATE = "PARSER_CANDIDATE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"

_CORE_PATTERNS = {
    "armor_class": re.compile(r"\b(?:classe\s+armatura|ca)\b", re.IGNORECASE),
    "hit_points": re.compile(r"\b(?:punti\s+ferita|pf)\b", re.IGNORECASE),
    "speed": re.compile(r"\bvelocit[aà]\b", re.IGNORECASE),
    "actions": re.compile(r"\bazioni\b", re.IGNORECASE),
}

_ABILITY_PATTERNS = {
    "for": re.compile(r"\b(?:forza|for)\b", re.IGNORECASE),
    "des": re.compile(r"\b(?:destrezza|des)\b", re.IGNORECASE),
    "cos": re.compile(r"\b(?:costituzione|cos)\b", re.IGNORECASE),
    "int": re.compile(r"\b(?:intelligenza|int)\b", re.IGNORECASE),
    "sag": re.compile(r"\b(?:saggezza|sag)\b", re.IGNORECASE),
    "car": re.compile(r"\b(?:carisma|car)\b", re.IGNORECASE),
}


def _word_count(text: str) -> int:
    return len(re.findall(r"[^\W\d_]{2,}", text or "", flags=re.UNICODE))


def evaluate_ocr_parser_readiness(text: Any) -> dict[str, Any]:
    """Return structural evidence only; never parse or persist source content."""
    value = str(text or "")
    core_hits = sorted(name for name, pattern in _CORE_PATTERNS.items() if pattern.search(value))
    ability_hits = sorted(name for name, pattern in _ABILITY_PATTERNS.items() if pattern.search(value))
    words = _word_count(value)

    # Conservative gate: a monster stat block should expose the three core
    # defensive/movement labels and most ability headings. "Azioni" is useful
    # evidence but not mandatory because a bounded page may split the block.
    required_core = {"armor_class", "hit_points", "speed"}
    candidate = required_core.issubset(core_hits) and len(ability_hits) >= 4 and words >= 80

    return {
        "classification": PARSER_CANDIDATE if candidate else REVIEW_REQUIRED,
        "word_count": words,
        "core_marker_hits": core_hits,
        "core_marker_count": len(core_hits),
        "ability_marker_hits": ability_hits,
        "ability_marker_count": len(ability_hits),
        "requires_manual_review": True,
        "parser_execution_authorized": False,
        "automatic_import_authorized": False,
        "database_write_authorized": False,
        "canonicalization_authorized": False,
    }


def main() -> int:
    text = sys.stdin.read()
    print(json.dumps(evaluate_ocr_parser_readiness(text), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
