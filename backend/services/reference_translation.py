"""Provider-independent helpers for conservative reference localization.

The source snapshot is immutable. Localized fields are a convenience layer for
Italian search/display and are never proof that the underlying rule is correct.
Provider transport stays in ``services.library``; this module owns only the
language policy, prompt contract, validation, and safe record transformation.
"""
from __future__ import annotations

import copy
import json
from typing import Any, Iterable

from reference_library import clean_text, compact_text, normalize_reference_name

TARGET_LANGUAGE = "it"
TRANSLATABLE_SOURCE_LANGUAGES = frozenset({"en", "es", "ru"})
TRANSLATION_REVIEW_FLAG = "traduzione_da_verificare"

_LANGUAGE_NAMES = {
    "en": "inglese",
    "es": "spagnolo",
    "ru": "russo",
    "it": "italiano",
}


def normalize_language(value: Any) -> str:
    return str(value or "").strip().casefold().replace("_", "-").split("-", 1)[0]


def translation_required(source_language: Any, target_language: str = TARGET_LANGUAGE) -> bool:
    source = normalize_language(source_language)
    target = normalize_language(target_language)
    return bool(source and target and source != target and source in TRANSLATABLE_SOURCE_LANGUAGES)


def translation_source_record(record: dict) -> dict:
    """Return only immutable source fields that may be sent to a translator."""
    return {
        "id": record["id"],
        "name": record.get("source_name") or record.get("name") or "",
        "description": record.get("source_description") or record.get("description") or "",
        "full_text": record.get("source_full_text") or record.get("full_text") or "",
        "attributes": copy.deepcopy(
            record.get("source_attributes")
            if record.get("source_attributes") is not None
            else record.get("attributes") or {}
        ),
    }


def build_translation_prompt(
    records: Iterable[dict],
    source_language: str,
    target_language: str = TARGET_LANGUAGE,
) -> str:
    source = normalize_language(source_language)
    target = normalize_language(target_language)
    if source not in TRANSLATABLE_SOURCE_LANGUAGES:
        raise ValueError(f"unsupported_source_language:{source or 'unknown'}")
    if target != TARGET_LANGUAGE:
        raise ValueError(f"unsupported_target_language:{target or 'unknown'}")

    source_rows = [translation_source_record(record) for record in records]
    if not source_rows:
        raise ValueError("translation_batch_empty")

    source_label = _LANGUAGE_NAMES.get(source, source)
    target_label = _LANGUAGE_NAMES.get(target, target)
    return (
        f"Traduci fedelmente dal {source_label} al {target_label} questi record strutturati "
        "di un manuale di gioco. Il testo fornito è la fonte: non usare conoscenze esterne. "
        "Traduci nome, descrizione, full_text e soltanto i valori testuali di attributes. "
        "Non aggiungere regole, non correggere il contenuto, non riassumere e non omettere "
        "dettagli. Mantieni invariati ID, numeri, dadi, formule, unità, sigle e struttura "
        "delle chiavi. Se un nome proprio o termine tecnico non è traducibile con certezza, "
        "conservalo invece di inventare una traduzione. Restituisci esclusivamente JSON valido "
        "nel formato {\"records\":[{\"id\":\"...\",\"name\":\"...\","
        "\"description\":\"...\",\"full_text\":\"...\",\"attributes\":{...}}]}. "
        "Ogni ID ricevuto deve comparire esattamente una volta e non devono comparire ID extra.\n\n"
        + json.dumps(source_rows, ensure_ascii=False, separators=(",", ":"))
    )


def validate_translation_payload(payload: object, records: Iterable[dict]) -> tuple[dict[str, dict], str]:
    """Validate a provider response without accepting partial or invented batches."""
    source_records = list(records)
    expected_ids = {str(record["id"]) for record in source_records}
    rows = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return {}, "provider_translation_invalid"

    translated: dict[str, dict] = {}
    seen: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            return {}, "provider_translation_invalid"
        record_id = str(item.get("id") or "")
        if not record_id or record_id not in expected_ids or record_id in seen:
            return {}, "provider_translation_invalid"
        seen.add(record_id)
        name = clean_text(str(item.get("name") or ""))
        description = clean_text(str(item.get("description") or ""))
        full_text = clean_text(str(item.get("full_text") or ""))
        attributes = item.get("attributes")
        if not name or not description or not full_text or not isinstance(attributes, dict):
            return {}, "provider_translation_incomplete"
        translated[record_id] = {
            "name": name,
            "description": compact_text(description),
            "full_text": full_text,
            "attributes": copy.deepcopy(attributes),
        }

    if seen != expected_ids:
        return {}, "provider_translation_incomplete"
    return translated, ""


def apply_translation(record: dict, translated: dict) -> dict:
    """Apply localized display fields while keeping immutable source provenance."""
    localized = copy.deepcopy(record)

    # Backfill an immutable source snapshot before replacing display fields.
    localized.setdefault("source_name", record.get("name") or "")
    localized.setdefault("source_description", record.get("description") or "")
    localized.setdefault("source_full_text", record.get("full_text") or "")
    localized.setdefault("source_attributes", copy.deepcopy(record.get("attributes") or {}))

    localized["name"] = translated["name"]
    localized["normalized_name"] = normalize_reference_name(translated["name"])
    localized["description"] = translated["description"]
    localized["full_text"] = translated["full_text"]
    localized["attributes"] = copy.deepcopy(translated["attributes"])
    localized["translation_status"] = "translated"
    localized["translation_error"] = ""
    localized["review_flags"] = sorted(
        set(localized.get("review_flags") or []) | {TRANSLATION_REVIEW_FLAG}
    )
    return localized


def translation_failure(record: dict, error: str) -> dict:
    failed = copy.deepcopy(record)
    failed["translation_status"] = "failed"
    failed["translation_error"] = error or "provider_translation_failed"
    failed["review_flags"] = sorted(
        set(failed.get("review_flags") or []) | {TRANSLATION_REVIEW_FLAG}
    )
    return failed
