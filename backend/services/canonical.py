"""Deterministic, owner-scoped canonicalisation of private rule sources.

This module deliberately treats imported records as immutable candidates: a
canonical row is a copy of one candidate, never a synthesis of several texts.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import math
from hashlib import sha256
from typing import Any, Callable

import requests

from core.config import OPENAI_API_KEY, OPENAI_TEXT_MODEL, utc_now
from reference_library import (
    normalize_reference_name,
    reference_content_fingerprint,
    reference_effective_level,
    reference_effective_type,
)

logger = logging.getLogger("tomeforge")
SUPPORTED_RULESETS = frozenset({"2014"})
FINAL_STATES = frozenset({"verified", "conflict", "low_confidence", "excluded"})
Comparator = Callable[[list[dict]], dict[str, Any]]


def canonical_group_key(record: dict, ruleset: str = "2014") -> str:
    """Stable key; features are distinguished by their progression location."""
    if ruleset not in SUPPORTED_RULESETS:
        raise ValueError("Solo il ruleset D&D 5e 2014 è attualmente supportato")
    if record_ruleset(record) != ruleset:
        raise ValueError(f"La fonte appartiene al ruleset D&D 5e {record_ruleset(record)}")
    reference_type = reference_effective_type(record)
    parts = [
        "dnd5e", ruleset, str(record.get("user_id", "")),
        reference_type,
        record.get("normalized_name") or normalize_reference_name(record.get("name", "")),
    ]
    if reference_type in {"subclass", "class_feature", "ability"}:
        parts.extend((
            normalize_reference_name(record.get("parent_class", "")),
            normalize_reference_name(record.get("parent_subclass", "")),
        ))
    if reference_type in {"class_feature", "ability", "spell"}:
        parts.append(reference_effective_level(record))
    return ":".join(parts)


def canonical_id(group_key: str) -> str:
    return f"canon_{sha256(group_key.encode('utf-8')).hexdigest()[:24]}"


def record_ruleset(record: dict) -> str:
    """Read explicit edition metadata first and conservatively detect 2024 sources."""
    refs = [ref for ref in record.get("source_refs") or [] if isinstance(ref, dict)]
    metadata = [record, record.get("attributes") or {}, *refs]
    for item in metadata:
        value = str(item.get("ruleset") or item.get("edition") or item.get("edition_year") or "")
        if "2024" in value:
            return "2024"
        if "2014" in value:
            return "2014"
    source_names = " ".join(
        [str(record.get("source_key", "")), *(str(ref.get("filename", "")) for ref in refs)]
    )
    return "2024" if "2024" in source_names else "2014"


def is_character_sheet_source(record: dict) -> bool:
    names = [str(record.get("source_key", ""))]
    names.extend(str(ref.get("filename", "")) for ref in record.get("source_refs") or [] if isinstance(ref, dict))
    return any(name.casefold().startswith("scheda_personaggio") for name in names)


def source_record_is_excluded(record: dict) -> bool:
    """Exclude duplicate, obsolete, misidentified and document-only sources."""
    refs = [ref for ref in record.get("source_refs") or [] if isinstance(ref, dict)]
    statuses = {str(ref.get("source_status") or "").casefold() for ref in refs}
    statuses.discard("")
    if not statuses:
        return False
    excluded = {"duplicate", "misidentified", "document", "superseded"}
    return statuses.issubset(excluded)


def source_authority(record: dict) -> tuple[int, str, bool]:
    """Return explicit source rank; weak aids never outrank authoritative books."""
    refs = [ref for ref in record.get("source_refs") or [] if isinstance(ref, dict)]
    metadata = [record, *refs]
    explicit = next((
        str(item.get("authority_class") or "").casefold()
        for item in metadata if item.get("authority_class")
    ), "")
    role = next((
        str(item.get("source_role") or "").casefold()
        for item in metadata if item.get("source_role")
    ), "")
    status = next((
        str(item.get("source_status") or "").casefold()
        for item in metadata if item.get("source_status")
    ), "")

    if status in {"duplicate", "misidentified", "document"}:
        return 0, status, False
    if status == "superseded":
        return 12, "superseded", False
    if explicit == "official_errata":
        return 60, "official_errata", True
    if explicit == "official_ruling":
        return 55, "official_ruling", True
    if explicit == "official_revision":
        return 50, "official_revision", True
    if explicit == "reprint":
        return 40, "reprint", True
    if role == "visual_aid" or explicit == "extraction_aid" or role == "extraction_aid":
        return 8, explicit or role or "extraction_aid", False
    if role == "ingest_copy":
        return 25, explicit or "ingest_copy", False
    if explicit in {"official_source", "official_supplement"}:
        return 35, explicit, False
    if explicit == "licensed_translation":
        return 32, "licensed_translation", False
    if explicit == "community_licensed" or role in {"lower_authority", "community"}:
        return 20, explicit or role, False

    name = " ".join([str(record.get("source_key", ""))] + [
        str(ref.get("filename", "")) for ref in refs
    ]).casefold()
    revision = any(item.get("revision") or item.get("is_revision") for item in metadata)
    official = any(item.get("official") or item.get("official_source") for item in metadata)
    if revision:
        return 50, "official_revision", True
    known_official = any(token in name for token in (
        "manuale_del_giocatore", "manual del jugador", "guida_onnicomprensiva",
        "calderone-omnicomprensivo", "manuale-dei-mostri", "manuale-del-dungeon-master",
    ))
    if official or known_official:
        return 30, "legacy_official_source", False
    return 10, "derived", False

def provenance(records: list[dict]) -> list[dict]:
    later_exists = any(source_authority(record)[2] for record in records)
    entries = []
    for record in sorted(records, key=lambda row: str(row.get("id", ""))):
        rank, authority, later = source_authority(record)
        for ref in record.get("source_refs") or [{}]:
            entry = dict(ref) if isinstance(ref, dict) else {}
            entry.update({"source_record_id": record.get("id"), "authority_rank": rank,
                          "authority_class": authority,
                          "ruleset": record_ruleset(record),
                          "translation_is_canonical_authority": False,
                          "content_fingerprint": reference_content_fingerprint(record),
                          "temporal_role": "later_revision" if later else
                          ("historical" if later_exists else "contemporaneous")})
            entries.append(entry)
    return entries


def _best(records: list[dict]) -> dict:
    return sorted(records, key=lambda row: (-source_authority(row)[0], str(row.get("id", ""))))[0]


def _equivalent(records: list[dict]) -> bool:
    return len({reference_content_fingerprint(record) for record in records}) == 1


def _translation_needs_ai_review(record: dict) -> bool:
    return (
        record.get("translation_status") == "translated"
        and record.get("review_status") != "verified"
        and not record.get("review_corrections")
    )


_VISUAL_REVIEW_FLAGS = frozenset({
    "ocr_da_verificare",
    "riga_tabella_da_verificare",
    "sezione_potenzialmente_continua",
})


def _record_has_blocking_uncertainty(record: dict) -> bool:
    flags = {str(flag) for flag in (record.get("review_flags") or [])}
    return bool(flags & _VISUAL_REVIEW_FLAGS) or record.get("translation_status") in {"failed", "processing"}


def _record_needs_ai_review(record: dict) -> bool:
    if _translation_needs_ai_review(record):
        return True
    if record.get("translation_status") in {"failed", "processing"}:
        return True
    if record.get("review_flags"):
        return True
    if record.get("review_status") != "verified":
        return True
    return source_authority(record)[0] <= 10


def openai_comparator(candidates: list[dict]) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI comparator non configurato")
    supplied = [{"source_record_id": r.get("id"), "name": r.get("name"),
                 "source_full_text": r.get("source_full_text", ""),
                 "translated_or_display_full_text": r.get("full_text", ""),
                 "translation_status": r.get("translation_status", "not_required"),
                 "attributes": r.get("attributes", {}), "source_refs": provenance([r]),
                 "authority": {"rank": source_authority(r)[0], "class": source_authority(r)[1]}}
                for r in candidates]
    prompt = (
        "Compare rule-source candidates. Select exactly one supplied source_record_id; do not invent "
        "or merge content. Official errata and later official revisions outrank reprints, official "
        "books, and derived sources. A translation is not canonical merely because it is translated; "
        "compare it with source_full_text when present. "
        "content or identifiers. Return JSON {selected_source_record_id,confidence,notes,conflict_fields,status}. "
        "status must be verified, conflict, or low_confidence.\\n" + json.dumps(supplied, ensure_ascii=False)
    )
    response = requests.post("https://api.openai.com/v1/chat/completions", headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": OPENAI_TEXT_MODEL, "messages": [{"role": "system", "content": "Return strict JSON only."},
              {"role": "user", "content": prompt}], "response_format": {"type": "json_object"}, "temperature": 0},
        timeout=(10, 90))
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


async def _compare(comparator: Comparator, records: list[dict]) -> dict[str, Any]:
    if inspect.iscoroutinefunction(comparator):
        result = comparator(records)
    else:
        result = await asyncio.to_thread(comparator, records)
    return await result if inspect.isawaitable(result) else result


async def canonicalize_group(records: list[dict], ruleset: str = "2014", comparator: Comparator | None = None) -> dict:
    key = canonical_group_key(records[0], ruleset)
    selected = _best(records)
    state, confidence, notes, conflicts = "verified", 1.0, "Equivalent source records.", []
    requires_ai = not _equivalent(records) or any(_record_needs_ai_review(record) for record in records)
    if requires_ai:
        try:
            answer = await _compare(comparator or openai_comparator, records)
            selected_id = answer.get("selected_source_record_id") if isinstance(answer, dict) else None
            confidence = float(answer.get("confidence", 0)) if isinstance(answer, dict) else 0
            notes = str(answer.get("notes", "")) if isinstance(answer, dict) else ""
            conflicts = answer.get("conflict_fields", []) if isinstance(answer, dict) else []
            if selected_id not in {record.get("id") for record in records}:
                raise ValueError("AI selected an unknown source record")
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("AI returned an invalid confidence")
            if not isinstance(conflicts, list) or any(not isinstance(field, str) for field in conflicts):
                raise ValueError("AI returned invalid conflict fields")
            selected = next(record for record in records if record.get("id") == selected_id)
            highest_authority = max(source_authority(record)[0] for record in records)
            if source_authority(selected)[0] < highest_authority:
                raise ValueError("AI selected a source below the highest available authority")
            requested = answer.get("status", "low_confidence")
            if requested not in {"verified", "conflict", "low_confidence"}:
                raise ValueError("AI returned an invalid status")
            state = "verified" if requested == "verified" and confidence >= .8 and not conflicts else (
                "conflict" if requested == "conflict" or conflicts else "low_confidence")
            if state == "verified" and _record_has_blocking_uncertainty(selected):
                state = "low_confidence"
                confidence = min(confidence, .79)
                conflicts = [*conflicts, "visual_or_source_verification"]
                notes = (notes + " Verifica visiva o seconda fonte necessaria prima dell'uso canonico.").strip()
        except Exception as exc:  # provider errors must never certify a rule
            logger.warning("Canonical comparator unavailable: %s", exc)
            state, confidence, notes, conflicts = "conflict", 0.0, "Comparator unavailable or invalid response.", []
    source_refs = provenance(records)
    for entry in source_refs:
        entry["selected"] = entry.get("source_record_id") == selected.get("id")
    now = utc_now()
    row = {
        "id": canonical_id(key), "user_id": records[0]["user_id"], "canonical_key": key,
        "reference_type": reference_effective_type(selected), "normalized_name":
        selected.get("normalized_name") or normalize_reference_name(selected.get("name", "")),
        "name": selected.get("name", ""), "description": selected.get("description", ""),
        "full_text": selected.get("full_text", ""), "attributes": selected.get("attributes", {}),
        "parent_class": selected.get("parent_class", ""), "parent_subclass": selected.get("parent_subclass", ""),
        "level": reference_effective_level(selected), "source_record_ids": [r["id"] for r in sorted(records, key=lambda r: r["id"])],
        "source_refs": source_refs, "source_count": len(records), "confidence": confidence,
        "verification_status": state, "conflict_fields": conflicts,
        "verification_model": OPENAI_TEXT_MODEL if requires_ai else "deterministic",
        "verification_notes": notes, "created_at": now, "updated_at": now,
    }
    return row


async def canonicalization_status(user_id: str, *, db) -> dict:
    records = await db.private_reference_records.find({"user_id": user_id}).to_list(8000)
    canonical_rows = await db.private_reference_canonical.find({"user_id": user_id}).to_list(8000)
    counts = {key: 0 for key in ("verified", "conflict", "low_confidence", "pending")}
    groups: dict[str, list[dict]] = {}
    excluded = 0
    for record in records:
        if (
            is_character_sheet_source(record)
            or source_record_is_excluded(record)
            or record_ruleset(record) != "2014"
            or record.get("ai_review_status") == "excluded"
        ):
            excluded += 1
        else:
            groups.setdefault(canonical_group_key(record), []).append(record)
    for members in groups.values():
        member_states = {r.get("ai_review_status", "pending") for r in members}
        state = next(
            (candidate for candidate in ("conflict", "low_confidence", "pending", "verified")
             if candidate in member_states),
            "pending",
        )
        counts[state] += 1
    return {
        "owner_user_id": user_id, "ruleset": "2014", "total_groups": len(groups),
        "pending_groups": counts["pending"], "verified_groups": counts["verified"],
        "conflict_groups": counts["conflict"], "low_confidence_groups": counts["low_confidence"],
        "excluded_records": excluded, "records_total": len(records), "canonical_total": len(canonical_rows),
    }


async def run_canonicalization(user_id: str, *, db, batch_size: int = 5, ruleset: str = "2014",
                               comparator: Comparator | None = None) -> dict:
    if ruleset not in SUPPORTED_RULESETS:
        raise ValueError("Solo il ruleset D&D 5e 2014 è attualmente supportato")
    records = await db.private_reference_records.find({"user_id": user_id}).to_list(8000)
    groups: dict[str, list[dict]] = {}
    exclusions: list[tuple[dict, str]] = []
    for record in records:
        if is_character_sheet_source(record):
            exclusions.append((record, "Character sheet/template source excluded."))
            continue
        if source_record_is_excluded(record):
            exclusions.append((record, "Duplicate, superseded, misidentified or document source excluded."))
            continue
        source_ruleset = record_ruleset(record)
        if source_ruleset != ruleset:
            exclusions.append((record, f"Unsupported ruleset: dnd5e-{source_ruleset}."))
            continue
        groups.setdefault(canonical_group_key(record, ruleset), []).append(record)
    processed = 0
    for record, reason in sorted(exclusions, key=lambda item: str(item[0].get("id", ""))):
        if processed >= batch_size:
            break
        if record.get("ai_review_status") == "excluded" and record.get("ai_review_notes") == reason:
            continue
        await db.private_reference_records.update_one(
            {"id": record["id"], "user_id": user_id},
            {"$set": {
                "ai_review_status": "excluded",
                "ai_review_notes": reason,
                "ai_reviewed_at": utc_now(),
                "ai_review_corrections": {
                    "selected": False,
                    "ruleset": record_ruleset(record),
                },
                "canonical_id": None,
            }},
        )
        processed += 1
    for key in sorted(groups):
        if processed >= batch_size:
            break
        members = groups[key]
        cid = canonical_id(key)
        existing = await db.private_reference_canonical.find_one({"id": cid, "user_id": user_id})
        expected_source_ids = sorted(member["id"] for member in members)
        finalized_members = all(
            r.get("canonical_id") == cid and r.get("ai_review_status") in FINAL_STATES
            for r in members
        )
        canonical_is_current = (
            existing is not None
            and sorted(existing.get("source_record_ids") or []) == expected_source_ids
            and existing.get("verification_status") in FINAL_STATES
            and {
                ref.get("source_record_id"): ref.get("content_fingerprint")
                for ref in existing.get("source_refs") or []
                if isinstance(ref, dict) and ref.get("source_record_id")
            } == {
                member["id"]: reference_content_fingerprint(member)
                for member in members
            }
        )
        if finalized_members and canonical_is_current:
            continue
        row = await canonicalize_group(members, ruleset, comparator)
        if existing:
            row["created_at"] = existing.get("created_at", row["created_at"])
            await db.private_reference_canonical.update_one({"id": row["id"], "user_id": user_id}, {"$set": row})
        else:
            await db.private_reference_canonical.insert_one(row)
        selected_id = next(ref["source_record_id"] for ref in row["source_refs"] if ref["selected"])
        for member in members:
            selected = member["id"] == selected_id
            await db.private_reference_records.update_one({"id": member["id"], "user_id": user_id}, {"$set": {
                "canonical_id": row["id"], "ai_review_status": row["verification_status"],
                "ai_confidence": row["confidence"], "ai_review_model": row["verification_model"],
                "ai_reviewed_at": row["updated_at"], "ai_review_notes": row["verification_notes"],
                "ai_review_corrections": {"selected_source_record_id": selected_id,
                                          "selected": selected,
                                          "ruleset": ruleset,
                                          "canonical_source_refs": row["source_refs"]},
            }})
        processed += 1
    return {**await canonicalization_status(user_id, db=db), "processed_groups": processed}