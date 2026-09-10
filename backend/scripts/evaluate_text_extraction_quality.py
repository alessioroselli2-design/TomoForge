#!/usr/bin/env python3
"""Conservative, read-only text extraction quality preflight.

This helper identifies obviously corrupted extracted text before parser/import work.
It does not run OCR, mutate Supabase, retry imports, or authorize canonicalization.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from typing import Any

TEXT_USABLE = "TEXT_USABLE"
VISION_REVIEW_REQUIRED = "VISION_REVIEW_REQUIRED"
EMPTY_TEXT = "EMPTY_TEXT"

_ALLOWED_CONTROLS = {"\n", "\r", "\t"}


def _is_suspicious_control(char: str) -> bool:
    return unicodedata.category(char) == "Cc" and char not in _ALLOWED_CONTROLS


def evaluate_text_extraction_quality(text: Any) -> dict[str, Any]:
    """Return conservative diagnostics without attempting to repair the text."""
    value = str(text or "")
    if not value.strip():
        return {
            "classification": EMPTY_TEXT,
            "character_count": len(value),
            "suspicious_control_count": 0,
            "replacement_character_count": 0,
            "suspicious_character_ratio": 0.0,
            "requires_vision_review": True,
            "automatic_repair_authorized": False,
            "ocr_authorized": False,
            "database_write_authorized": False,
            "canonicalization_authorized": False,
        }

    suspicious_controls = sum(_is_suspicious_control(char) for char in value)
    replacements = value.count("\ufffd")
    suspicious_total = suspicious_controls + replacements
    ratio = suspicious_total / max(len(value), 1)

    # A single replacement character is enough to require review. For raw control
    # bytes, require repeated evidence so isolated formatting artifacts do not
    # unnecessarily force otherwise usable text into the vision path.
    corrupted = replacements > 0 or suspicious_controls >= 3 or ratio >= 0.01
    classification = VISION_REVIEW_REQUIRED if corrupted else TEXT_USABLE
    return {
        "classification": classification,
        "character_count": len(value),
        "suspicious_control_count": suspicious_controls,
        "replacement_character_count": replacements,
        "suspicious_character_ratio": round(ratio, 6),
        "requires_vision_review": corrupted,
        "automatic_repair_authorized": False,
        "ocr_authorized": False,
        "database_write_authorized": False,
        "canonicalization_authorized": False,
    }


def main() -> int:
    text = sys.stdin.read()
    print(json.dumps(evaluate_text_extraction_quality(text), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
