"""Preflight to a safe SQL proposal, never executing SQL.

The proposal is intentionally *not* an approval: a separate trusted reviewer
must attest source evidence before any transaction is authorized.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from monster_completion_preflight import preflight

UPDATABLE = ("name", "description", "full_text", "attributes", "translation_status")


def build_proposal(original: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Return a read-only, conditional update plan for one existing monster."""
    check = preflight(original, candidate)
    return {
        "record_id": original.get("id"),
        "ready": check.ready,
        "blockers": list(check.blockers),
        "proposed_fingerprint": check.proposed_fingerprint,
        "proposed_fields": {key: candidate.get(key) for key in UPDATABLE},
        "required_match": {
            "id": original.get("id"),
            "updated_at": original.get("updated_at"),
            "translation_status": original.get("translation_status"),
            "translation_lease_id": original.get("translation_lease_id"),
            "translation_lease_expires_at": original.get("translation_lease_expires_at"),
        },
        "writes_performed": 0,
        "requires_independent_source_review": True,
    }


def report_json(original: Mapping[str, Any], candidate: Mapping[str, Any]) -> str:
    return json.dumps(build_proposal(original, candidate), ensure_ascii=False, indent=2)
