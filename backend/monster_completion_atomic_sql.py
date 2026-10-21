"""Validate a single-record snapshot and emit a parameterized SQL *template*.

This code cannot execute SQL and is deliberately independent of Supabase.
The transaction must be run by a separate authorized executor only after
source evidence has been independently checked.
"""
from __future__ import annotations

from typing import Any, Mapping


def conditional_update_sql() -> str:
    """One-row compare-and-swap update, requiring the executor to bind values.

    Never interpolate text from a manual into this statement. The WHERE
    clause protects against stale snapshots and active translation leases.
    A zero-row result means the executor must stop and re-read.
    """
    return """
UPDATE public.private_reference_records
SET name = %(name)s,
    description = %(description)s,
    full_text = %(full_text)s,
    attributes = %(attributes)s::jsonb,
    translation_status = 'translated',
    translation_review_status = 'pending',
    translation_review_fingerprint = NULL,
    translation_review_confidence = NULL,
    translation_review_model = NULL,
    translation_reviewed_at = NULL,
    updated_at = now()
WHERE id = %(id)s
  AND updated_at IS NOT DISTINCT FROM %(expected_updated_at)s
  AND translation_status IS NOT DISTINCT FROM %(expected_translation_status)s
  AND coalesce(translation_lease_id, '') = ''
  AND coalesce(translation_lease_expires_at, 0) = 0
  AND source_language IS NOT DISTINCT FROM %(expected_source_language)s
  AND source_name IS NOT DISTINCT FROM %(expected_source_name)s
  AND source_description IS NOT DISTINCT FROM %(expected_source_description)s
  AND source_full_text IS NOT DISTINCT FROM %(expected_source_full_text)s
  AND source_attributes IS NOT DISTINCT FROM %(expected_source_attributes)s::jsonb
  AND source_refs IS NOT DISTINCT FROM %(expected_source_refs)s::jsonb
RETURNING id, updated_at, translation_status, translation_review_status;
""".strip()


def sql_bindings(original: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Prepare named bind values; does not run a query or attest source evidence."""
    import json

    if not original.get("id") or original.get("id") != candidate.get("id"):
        raise ValueError("record identity mismatch")
    return {
        "id": original["id"],
        "name": candidate.get("name"),
        "description": candidate.get("description"),
        "full_text": candidate.get("full_text"),
        "attributes": json.dumps(candidate.get("attributes") or {}, ensure_ascii=False),
        "expected_updated_at": original.get("updated_at"),
        "expected_translation_status": original.get("translation_status"),
        "expected_source_language": original.get("source_language"),
        "expected_source_name": original.get("source_name"),
        "expected_source_description": original.get("source_description"),
        "expected_source_full_text": original.get("source_full_text"),
        "expected_source_attributes": json.dumps(original.get("source_attributes") or {}, ensure_ascii=False),
        "expected_source_refs": json.dumps(original.get("source_refs") or [], ensure_ascii=False),
    }
