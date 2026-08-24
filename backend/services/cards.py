import copy
import logging
import uuid
from typing import Any, Literal, Optional

from fastapi import HTTPException
from reference_library import (
    reference_is_trusted,
    reference_rule_source,
    reference_snapshot,
    reference_snapshot_change_fields,
    reference_snapshot_changed,
    reference_to_card_payload,
)

from core.config import utc_now
from core.db import db as _singleton_db
from services.spells import private_spell_records

logger = logging.getLogger("tomeforge")


def _is_empty_card_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


CARD_HISTORY_LIMIT = 20
CARD_HISTORY_FIELDS = (
    "type", "custom_type", "name", "description", "story", "language",
    "attributes", "artwork_path", "frame", "appearance", "back",
    "reference_ids", "spell_ids", "rule_sources", "source_refs", "reference_snapshots",
)


def card_change_patch(before: dict, after: dict) -> tuple[dict, dict, list[str]]:
    """Return small before/after patches rather than duplicating whole cards."""
    previous: dict = {}
    current: dict = {}
    changed: list[str] = []
    for field in CARD_HISTORY_FIELDS:
        before_value = before.get(field)
        after_value = after.get(field)
        if before_value != after_value:
            previous[field] = copy.deepcopy(before_value)
            current[field] = copy.deepcopy(after_value)
            changed.append(field)
    return previous, current, changed


def append_card_history(
    history: list[dict],
    before: dict,
    after: dict,
    source: Literal["user", "manual"],
    action: Literal["update", "reference_update", "manual_completion"],
    reference_ids: Optional[list[str]] = None,
) -> list[dict]:
    """Append an account-owned card change, dropping redo entries after a new edit."""
    previous, current, changed = card_change_patch(before, after)
    if not changed:
        return copy.deepcopy(history or [])
    entry = {
        "id": str(uuid.uuid4()),
        "source": source,
        "action": action,
        "created_at": utc_now(),
        "changed_fields": changed,
        "before": previous,
        "after": current,
        "undone": False,
    }
    if reference_ids:
        entry["reference_ids"] = list(dict.fromkeys(reference_ids))
    active_history = [item for item in (history or []) if not item.get("undone")]
    return (active_history + [entry])[-CARD_HISTORY_LIMIT:]


def apply_history_entry(card: dict, entry: dict, direction: Literal["before", "after"]) -> dict:
    restored = copy.deepcopy(card)
    for field, value in (entry.get(direction) or {}).items():
        restored[field] = copy.deepcopy(value)
    return restored


async def save_card_versioned(card: dict, user_id: str, updates: dict, expected_version: int, *, db=None) -> dict:
    """Save only if this is still the version the caller read, avoiding lost edits."""
    _db = db if db is not None else _singleton_db
    stored_version = int(card.get("version", 0) or 0)
    if expected_version != stored_version:
        raise HTTPException(
            status_code=409,
            detail="La scheda è stata modificata altrove. Ricaricala prima di salvare o aggiornare le regole.",
        )
    saved_updates = {**updates, "version": stored_version + 1}
    result = await _db.cards.update_one(
        {"id": card["id"], "user_id": user_id, "version": stored_version},
        {"$set": saved_updates},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=409,
            detail="La scheda è stata modificata altrove. Ricaricala prima di salvare o aggiornare le regole.",
        )
    card.update(saved_updates)
    return card


async def insert_cards_atomically(cards: list, *, db=None) -> None:
    """Persist a linked-card set without exposing a partially written set."""
    _db = db if db is not None else _singleton_db
    documents = [card.model_dump() for card in cards]
    if not documents:
        return
    try:
        await _db.cards.insert_many(documents)
    except Exception:
        for document in documents:
            try:
                await _db.cards.delete_one({"id": document["id"]})
            except Exception:
                logger.exception("Failed to clean up a partially persisted linked card")
        raise


def character_default_fields(record: dict) -> tuple[tuple[str, Any], ...]:
    source = record.get("attributes") or {}
    reference_type = record.get("reference_type")
    if reference_type == "class":
        return (
            ("dadi_vita", source.get("dado_vita")),
            ("competenze", source.get("competenze")),
            ("tiri_salvezza", source.get("tiri_salvezza")),
        )
    if reference_type in {"race", "subrace"}:
        return (
            ("velocita", source.get("velocita")),
            ("linguaggi", source.get("linguaggi")),
            ("tratti_razza", source.get("tratti")),
        )
    if reference_type == "subclass":
        return (("abilita_sottoclasse", source.get("caratteristiche") or source.get("privilegi")),)
    return ()


def character_manual_defaults(records: list[dict], attributes: dict) -> dict:
    """Mirror only deterministic, missing character fields from trusted records."""
    completed = copy.deepcopy(attributes or {})
    for record in records:
        for field, value in character_default_fields(record):
            if _is_empty_card_value(completed.get(field)) and not _is_empty_card_value(value):
                completed[field] = copy.deepcopy(value)
    return completed


def reference_snapshot_for_card(record: dict, card_type: str, saved_at: str = "") -> dict:
    """Record both source text and the values that were derived from it."""
    snap = reference_snapshot(record, saved_at)
    if card_type != "character":
        return snap

    payload = reference_to_card_payload(record)
    derived = copy.deepcopy(payload.get("attributes") or {})
    reference_type = record.get("reference_type")
    name = record.get("name", "")
    reference_id = record.get("id", "")
    if reference_type == "class":
        derived["classe"] = name
    elif reference_type in {"race", "subrace"}:
        derived["razza"] = name
    elif reference_type == "subclass":
        derived["sottoclasse"] = name
    else:
        list_field = (
            "privilegi" if reference_type in {"class_feature", "ability", "feat"}
            else "incantesimi" if reference_type == "spell"
            else "equipaggiamento" if reference_type in {
                "weapon", "armor", "shield", "equipment", "tool", "magic_item",
                "vehicle", "ammunition", "mount", "trade_good", "service",
            }
            else ""
        )
        if list_field:
            derived[list_field] = [{
                "reference_id": reference_id,
                "nome": name,
                "descrizione": payload.get("description", ""),
            }]
    snap["derived_attributes"] = derived
    snap["derived_card_fields"] = {}
    return snap


async def reference_records_by_id(user_id: str, reference_ids: list[str], *, db=None) -> dict[str, dict]:
    from services.library import private_reference_records
    requested = set(reference_ids)
    return {
        record["id"]: record
        for record in await private_reference_records(user_id, db=db)
        if record.get("id") in requested
    }


def reference_snapshots_for_card(
    existing_snapshots: list[dict],
    records_by_id: dict[str, dict],
    reference_ids: list[str],
    card_type: str,
    saved_at: str,
) -> list[dict]:
    """Keep acknowledged snapshots for existing links; baseline only new links."""
    existing_by_id = {
        snapshot.get("reference_id"): snapshot
        for snapshot in existing_snapshots or []
        if snapshot.get("reference_id")
    }
    snapshots = []
    for reference_id in reference_ids:
        if reference_id in existing_by_id:
            snapshots.append(existing_by_id[reference_id])
        elif reference_id in records_by_id:
            snapshots.append(reference_snapshot_for_card(records_by_id[reference_id], card_type, saved_at))
    return snapshots


async def resolve_reference_provenance(user_id: str, reference_ids: list[str], *, db=None) -> tuple[list[str], list[dict]]:
    """Validate selected reference records and derive their immutable provenance."""
    import json
    from services.library import private_reference_records
    requested_ids = list(dict.fromkeys(reference_id for reference_id in reference_ids if reference_id))
    if not requested_ids:
        return [], []
    records_by_id = {
        record["id"]: record
        for record in await private_reference_records(user_id, db=db)
        if record.get("id") in requested_ids
    }
    missing = [reference_id for reference_id in requested_ids if reference_id not in records_by_id]
    if missing:
        raise HTTPException(status_code=404, detail="Uno o più riferimenti normativi non sono più disponibili")
    unverified = [
        reference_id for reference_id in requested_ids
        if not reference_is_trusted(records_by_id[reference_id])
    ]
    if unverified:
        raise HTTPException(
            status_code=409,
            detail="Uno o più riferimenti sono da verificare e non possono essere collegati come dati certi.",
        )
    sources: list[dict] = []
    seen_sources: set[str] = set()
    for reference_id in requested_ids:
        for source in records_by_id[reference_id].get("source_refs", []):
            key = json.dumps(source, sort_keys=True, ensure_ascii=False)
            if key not in seen_sources:
                seen_sources.add(key)
                sources.append(source)
    return requested_ids, sources


async def normalize_generic_spell_links(
    user_id: str,
    reference_ids: list[str],
    spell_ids: list[str],
    *,
    db=None,
) -> tuple[list[str], list[str]]:
    """Move generic spell references out of the retired Grimorio ID list.

    Older editor drafts can still contain a generic private-reference ID in
    ``spell_ids``. Keeping it there makes card saving look in ``private_spells``
    and incorrectly report that the spell disappeared.
    """
    from services.library import private_reference_records

    requested_spell_ids = list(dict.fromkeys(spell_id for spell_id in spell_ids if spell_id))
    if not requested_spell_ids:
        return list(dict.fromkeys(reference_id for reference_id in reference_ids if reference_id)), []
    generic_spell_ids = {
        record["id"]
        for record in await private_reference_records(user_id, db=db)
        if record.get("id") in requested_spell_ids and record.get("reference_type") == "spell"
    }
    normalized_reference_ids = list(dict.fromkeys([
        *(reference_id for reference_id in reference_ids if reference_id),
        *(spell_id for spell_id in requested_spell_ids if spell_id in generic_spell_ids),
    ]))
    legacy_spell_ids = [spell_id for spell_id in requested_spell_ids if spell_id not in generic_spell_ids]
    return normalized_reference_ids, legacy_spell_ids


async def resolve_spell_provenance(user_id: str, spell_ids: list[str], *, db=None) -> tuple[list[str], list[dict]]:
    """Validate private Grimorio entries and derive their manual/page links."""
    import json
    from reference_library import reference_review_reason
    requested_ids = list(dict.fromkeys(spell_id for spell_id in spell_ids if spell_id))
    if not requested_ids:
        return [], []
    records_by_id = {
        spell["id"]: spell
        for spell in await private_spell_records(user_id, db=db)
        if spell.get("id") in requested_ids
    }
    missing = [spell_id for spell_id in requested_ids if spell_id not in records_by_id]
    if missing:
        raise HTTPException(status_code=404, detail="Uno o più incantesimi del Grimorio non sono più disponibili")
    unverified = [spell_id for spell_id in requested_ids if not reference_is_trusted(records_by_id[spell_id])]
    if unverified:
        reason = reference_review_reason(records_by_id[unverified[0]])
        raise HTTPException(
            status_code=409,
            detail=reason or "Uno o più incantesimi sono da verificare e non possono essere collegati come dati certi.",
        )
    sources: list[dict] = []
    seen_sources: set[str] = set()
    for spell_id in requested_ids:
        for source in records_by_id[spell_id].get("source_refs", []):
            key = json.dumps(source, sort_keys=True, ensure_ascii=False)
            if key not in seen_sources:
                seen_sources.add(key)
                sources.append(source)
    return requested_ids, sources


def merge_source_refs(*source_groups: list[dict]) -> list[dict]:
    """Merge already-validated source metadata without trusting client input."""
    import json
    sources: list[dict] = []
    seen_sources: set[str] = set()
    for source_group in source_groups:
        for source in source_group:
            key = json.dumps(source, sort_keys=True, ensure_ascii=False)
            if key not in seen_sources:
                seen_sources.add(key)
                sources.append(source)
    return sources


async def rule_sources_for_card(user_id: str, reference_ids: list[str], spell_ids: list[str], *, db=None) -> list[dict]:
    """Build one safe manual/page entry for every server-validated linked rule."""
    from services.library import private_reference_records
    references = {
        record["id"]: record
        for record in await private_reference_records(user_id, db=db)
        if record.get("id") in reference_ids
    }
    spells = {
        spell["id"]: spell
        for spell in await private_spell_records(user_id, db=db)
        if spell.get("id") in spell_ids
    }
    return [
        reference_rule_source(references[reference_id])
        for reference_id in reference_ids
        if reference_id in references
    ] + [
        {
            "source_kind": "spell",
            "source_id": spell_id,
            "name": spells[spell_id].get("name", ""),
            "reference_type": "spell",
            "source_refs": spells[spell_id].get("source_refs", []),
        }
        for spell_id in spell_ids
        if spell_id in spells
    ]


async def manual_completion_preview_for_card(card: dict, user_id: str, *, db=None) -> tuple[dict, list[dict], list[str]]:
    """Resolve exact, trusted manual records from the saved character identity."""
    from services.library import private_reference_records
    from reference_library import normalize_reference_name
    attributes = card.get("attributes") or {}
    lookups = (
        (attributes.get("classe"), {"class"}),
        (attributes.get("sottoclasse"), {"subclass"}),
        (attributes.get("razza"), {"race", "subrace"}),
        (attributes.get("sottorazza"), {"subrace"}),
    )
    records: list[dict] = []
    seen_ids: set[str] = set()
    available = await private_reference_records(user_id, db=db)
    linked_ids = set(card.get("reference_ids") or [])
    if linked_ids:
        records = [
            record for record in available
            if record.get("id") in linked_ids and reference_is_trusted(record)
        ]
        seen_ids = {record["id"] for record in records}
    for query, allowed_types in (() if linked_ids else lookups):
        normalized_query = normalize_reference_name(str(query or ""))
        if not normalized_query:
            continue
        for record in available:
            if (
                record.get("reference_type") in allowed_types
                and record.get("normalized_name") == normalized_query
                and reference_is_trusted(record)
                and record.get("id") not in seen_ids
            ):
                records.append(record)
                seen_ids.add(record["id"])
    completed = copy.deepcopy(attributes)
    field_sources: dict[str, dict] = {}
    for record in records:
        for field, value in character_default_fields(record):
            if _is_empty_card_value(completed.get(field)) and not _is_empty_card_value(value):
                completed[field] = copy.deepcopy(value)
                field_sources[field] = reference_rule_source(record)
    changes = [
        {
            "field": field,
            "before": copy.deepcopy(attributes.get(field)),
            "after": copy.deepcopy(completed[field]),
            "rule_source": field_sources.get(field),
        }
        for field in completed
        if completed[field] != attributes.get(field)
    ]
    return completed, changes, [record["id"] for record in records]


def refresh_derived_attributes(attributes: dict, old_snapshot: dict, new_snapshot: dict) -> tuple[dict, list[str]]:
    """Refresh only values that still equal the prior derived version."""
    refreshed = copy.deepcopy(attributes or {})
    protected: list[str] = []
    old_values = old_snapshot.get("derived_attributes") or {}
    new_values = new_snapshot.get("derived_attributes") or {}
    reference_id = old_snapshot.get("reference_id")
    for field, new_value in new_values.items():
        old_value = old_values.get(field)
        current_value = refreshed.get(field)
        if (
            isinstance(new_value, list)
            and all(isinstance(entry, dict) and entry.get("reference_id") == reference_id for entry in new_value)
        ):
            current_entries = current_value if isinstance(current_value, list) else []
            old_entries = old_value if isinstance(old_value, list) else []
            matching_entries = [
                entry for entry in current_entries
                if isinstance(entry, dict) and entry.get("reference_id") == reference_id
            ]
            untouched_entries = [
                entry for entry in current_entries
                if not (isinstance(entry, dict) and entry.get("reference_id") == reference_id)
            ]
            unchanged_entries = [entry for entry in matching_entries if entry in old_entries]
            manual_entries = [entry for entry in matching_entries if entry not in old_entries]
            if manual_entries or (old_entries and not matching_entries):
                refreshed[field] = untouched_entries + copy.deepcopy(manual_entries)
                protected.append(field)
            else:
                refreshed[field] = untouched_entries + copy.deepcopy(new_value)
        elif _is_empty_card_value(current_value) or current_value == old_value:
            refreshed[field] = copy.deepcopy(new_value)
        elif current_value != new_value:
            protected.append(field)
    return refreshed, protected


def reference_update_report(card: dict, records_by_id: dict[str, dict]) -> list[dict]:
    """Describe current reference changes without modifying the saved card."""
    snapshots_by_id = {
        snapshot.get("reference_id"): snapshot
        for snapshot in card.get("reference_snapshots") or []
        if snapshot.get("reference_id")
    }
    updates = []
    for reference_id in card.get("reference_ids") or []:
        snapshot = snapshots_by_id.get(reference_id)
        record = records_by_id.get(reference_id)
        if not record:
            updates.append({
                "reference_id": reference_id,
                "status": "missing",
                "before": snapshot,
                "after": None,
                "changed_fields": ["fonte non disponibile"],
            })
        elif not snapshot:
            updates.append({
                "reference_id": reference_id,
                "status": "untracked",
                "before": None,
                "after": reference_snapshot_for_card(record, card.get("type", "custom")),
                "changed_fields": [],
            })
        elif reference_snapshot_changed(snapshot, record):
            updates.append({
                "reference_id": reference_id,
                "status": "updated",
                "before": snapshot,
                "after": reference_snapshot_for_card(record, card.get("type", "custom")),
                "changed_fields": reference_snapshot_change_fields(snapshot, record),
            })
    return updates


def remove_unlinked_reference_attributes(attributes: dict, reference_ids: list[str]) -> dict:
    """Keep manual entries while dropping list entries derived from removed records."""
    allowed_ids = set(reference_ids)
    reconciled = copy.deepcopy(attributes or {})
    for field in ("privilegi", "incantesimi", "equipaggiamento"):
        entries = reconciled.get(field)
        if isinstance(entries, list):
            reconciled[field] = [
                entry for entry in entries
                if not isinstance(entry, dict)
                or not entry.get("reference_id")
                or entry["reference_id"] in allowed_ids
            ]
    return reconciled
