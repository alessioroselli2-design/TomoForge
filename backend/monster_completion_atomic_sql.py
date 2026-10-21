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
    translation_review_fingerprint = '',
    translation_review_notes = '',
    translation_review_conflict_fields = '[]'::jsonb,
    translation_review_confidence = 0,
    translation_review_model = '',
    translation_reviewed_at = NULL,
    translation_error = '',
    updated_at = now()
WHERE id = %(id)s
  AND updated_at IS NOT DISTINCT FROM %(expected_updated_at)s
  AND translation_status IS NOT DISTINCT FROM %(expected_translation_status)s
  AND translation_review_status IS NOT DISTINCT FROM %(expected_translation_review_status)s
  AND coalesce(translation_lease_id, '') = ''
  AND coalesce(translation_lease_expires_at, 0) = 0
  AND review_status IS NOT DISTINCT FROM %(expected_review_status)s
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
        "expected_translation_review_status": original.get("translation_review_status"),
        "expected_review_status": original.get("review_status"),
        "expected_source_language": original.get("source_language"),
        "expected_source_name": original.get("source_name"),
        "expected_source_description": original.get("source_description"),
        "expected_source_full_text": original.get("source_full_text"),
        "expected_source_attributes": json.dumps(original.get("source_attributes") or {}, ensure_ascii=False),
        "expected_source_refs": json.dumps(original.get("source_refs") or [], ensure_ascii=False),
    }

def audited_update_sql() -> str:
    """Atomic audited update; bind only the JSON payload from audited_sql_bindings.

    The typed whole-row comparison protects every source, identity, content and
    review column, including fields not otherwise mentioned by this module.
    Matching JSON keys also requires an actual complete row snapshot. A zero-row
    result requires a fresh read and audit; it must never be retried blindly.
    """
    return """
WITH input AS (
    SELECT %(payload)s::jsonb AS data
), expected AS (
    SELECT data,
           jsonb_populate_record(NULL::public.private_reference_records,
                                 data->'original') AS snapshot
    FROM input
)
UPDATE public.private_reference_records AS target
SET name = expected.data->'candidate'->>'name',
    description = expected.data->'candidate'->>'description',
    full_text = expected.data->'candidate'->>'full_text',
    attributes = expected.data->'candidate'->'attributes',
    translation_status = 'translated',
    translation_review_status = 'ai_verified',
    translation_review_fingerprint = expected.data->'audit'->>'candidate_fingerprint',
    translation_review_notes = (expected.data->'audit')::text,
    translation_review_conflict_fields = '[]'::jsonb,
    translation_review_confidence = (expected.data->'audit'->>'review_confidence')::numeric,
    translation_review_model = expected.data->'audit'->>'reviewer_id',
    translation_reviewed_at = (expected.data->'audit'->>'reviewed_at')::timestamptz,
    translation_error = '',
    updated_at = (expected.data->'audit'->>'reviewed_at')::timestamptz
FROM expected
WHERE target.id = (expected.snapshot).id
  AND target.reference_type = 'monster'
  AND target.translation_lease_id = ''
  AND target.translation_lease_expires_at = 0
  AND target IS NOT DISTINCT FROM expected.snapshot
  AND ARRAY(SELECT key FROM jsonb_object_keys(to_jsonb(target)) AS key ORDER BY key)
      = ARRAY(SELECT key FROM jsonb_object_keys(expected.data->'original') AS key ORDER BY key)
RETURNING target.id, target.updated_at, target.translation_status,
          target.translation_review_status, target.translation_review_fingerprint;
""".strip()


def audited_sql_bindings(
    original: Mapping[str, Any], candidate: Mapping[str, Any], audit: Mapping[str, Any],
) -> dict[str, str]:
    """Validate a completed external source audit, then serialize one SQL value.

    This function cannot inspect a PDF or perform an independent review. The
    caller must supply their completed evidence receipt; numeric confidence is
    accepted only alongside all evidence gates and the exact reviewed content.
    """
    import json
    import math
    import re
    from datetime import datetime, timedelta
    from urllib.parse import urlsplit

    from monster_completion_preflight import preflight

    if original.get("reference_type") != "monster":
        raise ValueError("original is not a monster")
    if (original.get("translation_lease_id") != ""
            or original.get("translation_lease_expires_at") != 0):
        raise ValueError("original has an active or unknown translation lease")
    if not original.get("user_id") or not original.get("updated_at"):
        raise ValueError("original identity/timestamp snapshot is incomplete")
    for key in ("id", "reference_type", "user_id"):
        if candidate.get(key) != original.get(key):
            raise ValueError(f"immutable identity changed: {key}")
    source_keys = {key for key in original if key.startswith("source_")}
    if source_keys != {key for key in candidate if key.startswith("source_")}:
        raise ValueError("source snapshot fields changed")
    for key in source_keys:
        if candidate[key] != original[key]:
            raise ValueError(f"immutable source changed: {key}")
    for flag in ("source_page_checked", "independent_review", "source_sections_checked"):
        if audit.get(flag) is not True:
            raise ValueError(f"completed audit gate missing: {flag}")
    result = preflight(
        original, candidate, source_page_checked=True,
        independent_review=True, source_sections_checked=True,
    )
    if not result.ready:
        raise ValueError(f"preflight failed: {', '.join(result.blockers)}")
    if audit.get("record_id") != original.get("id"):
        raise ValueError("audit record identity mismatch")
    if audit.get("candidate_fingerprint") != result.proposed_fingerprint:
        raise ValueError("audit candidate fingerprint mismatch")
    for key in ("reviewer_id", "review_notes", "source_url"):
        if not isinstance(audit.get(key), str) or not audit[key].strip():
            raise ValueError(f"audit field missing: {key}")
    source_url = urlsplit(audit["source_url"])
    if (source_url.scheme not in ("https", "http") or not source_url.hostname
            or source_url.username or source_url.password or source_url.query or source_url.fragment):
        raise ValueError("source_url must be a public evidence locator without credentials or query")
    digest = audit.get("source_evidence_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("source evidence SHA256 missing or invalid")
    page = audit.get("source_page")
    if not isinstance(page, int) or isinstance(page, bool) or page <= 0:
        raise ValueError("source evidence page missing or invalid")
    direct_source_match = any(
        ref.get("physical_sha256") == digest and ref.get("page") == page
        for ref in original.get("source_refs", []) if isinstance(ref, dict)
    )
    if not direct_source_match:
        _validate_minecraft_authority_mapping(original, audit)
    confidence = audit.get("review_confidence")
    if (not isinstance(confidence, (int, float)) or isinstance(confidence, bool)
            or not math.isfinite(confidence) or not 0.97 <= confidence <= 1):
        raise ValueError("completed review confidence must be finite and within [0.97, 1]")
    try:
        reviewed_at = datetime.fromisoformat(audit["reviewed_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError, TypeError) as exc:
        raise ValueError("reviewed_at must be an explicit UTC timestamp") from exc
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() != timedelta(0):
        raise ValueError("reviewed_at must be an explicit UTC timestamp")
    receipt = dict(audit)
    receipt["reviewed_at"] = reviewed_at.isoformat().replace("+00:00", "Z")
    for key in ("name", "description", "full_text"):
        if not isinstance(candidate.get(key), str) or not candidate[key].strip():
            raise ValueError(f"localized field missing: {key}")
    payload = {
        "original": dict(original),
        "candidate": {key: candidate[key] for key in ("name", "description", "full_text", "attributes")},
        "audit": receipt,
    }
    return {"payload": json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True)}


def _validate_minecraft_authority_mapping(
    original: Mapping[str, Any], audit: Mapping[str, Any],
) -> None:
    """Accept only the independently checked, registered Minecraft substitution.

    This bounded receipt does not assert that unavailable compilation bytes were
    rehashed. It records the archived digest separately from the official PDF
    actually checked; every original source_* value remains unchanged.
    """
    from reference_sources import source_metadata_for_page

    official_url = (
        "https://www.minecraft.net/content/dam/minecraftnet/games/minecraft/"
        "software/Minecraft-Monstrous-Compendium.pdf"
    )
    official_digest = "559802923408bb57ccea250e6806603ee20b1ad4ed28e58c2e1608bf5ba79521"
    archived_digest = "b7fb95c7519fb0936bb2cb37cfb6a5493134c86e0dc31196a4c62a67887e8ada"
    mapping = audit.get("provenance_mapping")
    if not isinstance(mapping, dict):
        raise ValueError("source mismatch requires a completed registered provenance mapping")
    if (audit.get("source_url") != official_url
            or audit.get("source_evidence_sha256") != official_digest):
        raise ValueError("unrecognized authoritative Minecraft evidence")
    if (mapping.get("independently_checked") is not True
            or mapping.get("original_digest_from_record_only") is not True
            or mapping.get("reviewer_id") != audit.get("reviewer_id")
            or not isinstance(mapping.get("mapping_reason"), str)
            or not mapping["mapping_reason"].strip()):
        raise ValueError("provenance mapping review receipt is incomplete")
    expected = {
        "original_filename": "701858566-RRN5YRR.pdf",
        "original_sha256": archived_digest,
        "logical_source_id": "mc_v3_minecraft_2023_en",
        "authoritative_sha256": official_digest,
        "authoritative_page": audit["source_page"],
        "authoritative_url": official_url,
    }
    if any(mapping.get(key) != value for key, value in expected.items()):
        raise ValueError("provenance mapping identity does not match registered source")
    original_page = mapping.get("original_page")
    if (not isinstance(original_page, int) or isinstance(original_page, bool)
            or not 28 <= original_page <= 33 or audit["source_page"] != original_page - 26):
        raise ValueError("Minecraft authoritative/compilation page mapping is invalid")
    if not any(
        ref.get("filename") == expected["original_filename"]
        and ref.get("physical_sha256") == archived_digest
        and ref.get("page") == original_page
        and ref.get("logical_source_id") == expected["logical_source_id"]
        for ref in original.get("source_refs", []) if isinstance(ref, dict)
    ):
        raise ValueError("mapped original provenance does not belong to this record")
    registered = source_metadata_for_page(expected["original_filename"], original_page)
    if (registered.get("logical_source_id") != expected["logical_source_id"]
            or registered.get("source_status") != "active"
            or registered.get("source_role") != "ingest_copy"
            or registered.get("authority_class") != "official_supplement"
            or registered.get("notes") != "Compilation ingest copy; standalone official source outranks when available"):
        raise ValueError("registry does not authorize this standalone source priority")


def render_audited_update(
    original: Mapping[str, Any], candidate: Mapping[str, Any], audit: Mapping[str, Any],
) -> str:
    """Render for an executor without bind support, keeping all values as data.

    A dollar-quote delimiter absent from the complete JSON payload prevents
    quotes, SQL fragments and delimiter-like manual text from becoming SQL.
    This function only returns SQL; it never connects to a database.
    """
    payload = audited_sql_bindings(original, candidate, audit)["payload"]
    delimiter_index = 0
    delimiter = "$tf_monster_0$"
    while delimiter in payload:
        delimiter_index += 1
        delimiter = f"$tf_monster_{delimiter_index}$"
    return audited_update_sql().replace("%(payload)s", f"{delimiter}{payload}{delimiter}")
