"""Pure helpers for invalidating stale translation-verification verdicts.

This module intentionally has no dependency on the reference parser or AI
services. Both layers can therefore enforce the same fingerprint without
creating an import cycle.
"""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any


def normalize_language(value: Any) -> str:
    return str(value or "").strip().casefold().replace("_", "-").split("-", 1)[0]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def translation_verification_fingerprint(record: dict) -> str:
    """Invalidate a prior verdict when either source or localized text changes."""
    payload = {
        "source_language": normalize_language(record.get("source_language")),
        "source_name": _clean(record.get("source_name")),
        "source_description": _clean(record.get("source_description")),
        "source_full_text": _clean(record.get("source_full_text")),
        "source_attributes": record.get("source_attributes") or {},
        "name": _clean(record.get("name")),
        "description": _clean(record.get("description")),
        "full_text": _clean(record.get("full_text")),
        "attributes": record.get("attributes") or {},
        "translation_status": str(record.get("translation_status") or "not_required"),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def translation_verification_is_current(record: dict) -> bool:
    stored = str(record.get("translation_review_fingerprint") or "")
    return bool(stored) and stored == translation_verification_fingerprint(record)
