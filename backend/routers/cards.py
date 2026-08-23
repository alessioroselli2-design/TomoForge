import copy
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from reference_library import reference_is_trusted, reference_rule_source, reference_snapshot_changed, reference_to_card_payload

from core.auth import get_current_user
from core.config import utc_now
from core.db import db
from schemas.cards import (
    Card, CardCreate, CardUpdate, CardVersionInput,
    LinkedCardInput, ManualCompletionInput, ReferenceUpdateInput,
)
from schemas.users import User
from services.cards import (
    append_card_history,
    apply_history_entry,
    card_change_patch,
    insert_cards_atomically,
    manual_completion_preview_for_card,
    merge_source_refs,
    reference_records_by_id,
    reference_snapshot_for_card,
    reference_snapshots_for_card,
    reference_update_report,
    refresh_derived_attributes,
    remove_unlinked_reference_attributes,
    resolve_reference_provenance,
    resolve_spell_provenance,
    rule_sources_for_card,
    save_card_versioned,
)
from services.library import (
    card_response,
    private_reference_records,
    public_card_payload,
    public_reference_update,
)

router = APIRouter()
logger = logging.getLogger("tomeforge")


def card_history_view(history: list[dict]) -> list[dict]:
    return public_card_payload({"change_history": history or []})["change_history"]


@router.post("/cards", response_model=Card)
async def create_card(body: CardCreate, user: User = Depends(get_current_user)):
    data = body.model_dump(exclude_none=True)
    reference_ids, reference_sources = await resolve_reference_provenance(user.user_id, data.get("reference_ids", []))
    spell_ids, spell_sources = await resolve_spell_provenance(user.user_id, data.get("spell_ids", []))
    data["reference_ids"] = reference_ids
    data["spell_ids"] = spell_ids
    data["source_refs"] = merge_source_refs(reference_sources, spell_sources)
    data["rule_sources"] = await rule_sources_for_card(user.user_id, reference_ids, spell_ids)
    data["attributes"] = remove_unlinked_reference_attributes(data.get("attributes", {}), reference_ids)
    records_by_id = await reference_records_by_id(user.user_id, reference_ids)
    data["reference_snapshots"] = reference_snapshots_for_card(
        [], records_by_id, reference_ids, data.get("type", "custom"), utc_now()
    )
    card = Card(user_id=user.user_id, **data)
    await db.cards.insert_one(card.model_dump())
    return card_response(card.model_dump())


@router.get("/cards", response_model=List[Card])
async def list_cards(type: Optional[str] = None, search: Optional[str] = None, user: User = Depends(get_current_user)):
    cards = await db.cards.find({"user_id": user.user_id}).sort("created_at", -1).to_list(1000)
    if type and type != "all":
        cards = [card for card in cards if card.get("type") == type]
    if search:
        needle = search.casefold()
        cards = [card for card in cards if needle in card.get("name", "").casefold()]
    return [card_response(card) for card in cards]


@router.get("/cards/{card_id}", response_model=Card)
async def get_card(card_id: str, user: User = Depends(get_current_user)):
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    return card_response(card)


@router.put("/cards/{card_id}", response_model=Card)
async def update_card(card_id: str, body: CardUpdate, user: User = Depends(get_current_user)):
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    before_card = copy.deepcopy(card)
    updates = body.model_dump(exclude_none=True)
    expected_version = updates.pop("version")
    if "reference_ids" in updates or "spell_ids" in updates:
        reference_ids, reference_sources = await resolve_reference_provenance(
            user.user_id, updates.get("reference_ids", card.get("reference_ids", []))
        )
        spell_ids, spell_sources = await resolve_spell_provenance(
            user.user_id, updates.get("spell_ids", card.get("spell_ids", []))
        )
        updates["reference_ids"] = reference_ids
        updates["spell_ids"] = spell_ids
        updates["source_refs"] = merge_source_refs(reference_sources, spell_sources)
        updates["rule_sources"] = await rule_sources_for_card(user.user_id, reference_ids, spell_ids)
        updates["attributes"] = remove_unlinked_reference_attributes(
            updates.get("attributes", card.get("attributes", {})),
            reference_ids,
        )
        records_by_id = await reference_records_by_id(user.user_id, reference_ids)
        updates["reference_snapshots"] = reference_snapshots_for_card(
            card.get("reference_snapshots", []),
            records_by_id,
            reference_ids,
            updates.get("type", card.get("type", "custom")),
            utc_now(),
        )
    else:
        updates.pop("source_refs", None)
        updates.pop("rule_sources", None)
    updates["updated_at"] = utc_now()
    after_card = copy.deepcopy(card)
    after_card.update(updates)
    updates["change_history"] = append_card_history(
        card.get("change_history", []),
        before_card,
        after_card,
        "user",
        "update",
    )
    await save_card_versioned(card, user.user_id, updates, expected_version)
    return card_response(card)


@router.get("/cards/{card_id}/reference-updates")
async def card_reference_updates(card_id: str, user: User = Depends(get_current_user)):
    """Return changed linked references and their saved/current private snapshots."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    records_by_id = await reference_records_by_id(user.user_id, card.get("reference_ids") or [])
    updates = reference_update_report(card, records_by_id)
    return {
        "updates": [public_reference_update(update) for update in updates],
        "updated_count": sum(update["status"] == "updated" for update in updates),
        "untracked_count": sum(update["status"] == "untracked" for update in updates),
    }


@router.post("/cards/{card_id}/manual-completion", response_model=Card)
async def complete_card_from_manuals(
    card_id: str,
    body: ManualCompletionInput,
    user: User = Depends(get_current_user),
):
    """Save a server-derived manual completion as a distinct, undoable event."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    if card.get("type") != "character":
        raise HTTPException(status_code=400, detail="Il completamento dai manuali è disponibile solo per i personaggi")

    before_card = copy.deepcopy(card)
    after_card = copy.deepcopy(card)
    completed_attributes, _changes, source_ids = await manual_completion_preview_for_card(card, user.user_id)
    after_card["attributes"] = completed_attributes
    history = append_card_history(
        card.get("change_history", []),
        before_card,
        after_card,
        "manual",
        "manual_completion",
        source_ids,
    )
    updates = {
        "attributes": after_card["attributes"],
        "change_history": history,
        "updated_at": utc_now(),
    }
    await save_card_versioned(card, user.user_id, updates, body.version)
    return card_response(card)


@router.get("/cards/{card_id}/manual-completion-preview")
async def card_manual_completion_preview(card_id: str, user: User = Depends(get_current_user)):
    """Calculate the exact trusted fields that a manual completion would add."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    if card.get("type") != "character":
        raise HTTPException(status_code=400, detail="Il completamento dai manuali è disponibile solo per i personaggi")
    attributes, changes, reference_ids = await manual_completion_preview_for_card(card, user.user_id)
    return {"attributes": attributes, "changes": changes, "reference_ids": reference_ids, "version": card.get("version", 0)}


@router.post("/cards/{card_id}/reference-updates")
async def refresh_card_reference_updates(
    card_id: str,
    body: ReferenceUpdateInput,
    user: User = Depends(get_current_user),
):
    """Apply selected current reference values without overwriting manual choices."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    before_card = copy.deepcopy(card)
    linked_ids = list(dict.fromkeys(card.get("reference_ids") or []))
    requested_ids = list(dict.fromkeys(body.reference_ids or linked_ids))
    if not set(requested_ids).issubset(linked_ids):
        raise HTTPException(status_code=400, detail="Puoi aggiornare solo riferimenti già collegati alla carta")
    records_by_id = await reference_records_by_id(user.user_id, requested_ids)
    missing = [reference_id for reference_id in requested_ids if reference_id not in records_by_id]
    if missing:
        raise HTTPException(status_code=404, detail="Uno o più riferimenti normativi non sono più disponibili")
    unverified = [reference_id for reference_id in requested_ids if not reference_is_trusted(records_by_id[reference_id])]
    if unverified:
        raise HTTPException(
            status_code=409,
            detail="Un riferimento aggiornato è da verificare e non può sostituire dati regolamentari.",
        )

    snapshots_by_id = {
        snapshot.get("reference_id"): snapshot
        for snapshot in card.get("reference_snapshots") or []
        if snapshot.get("reference_id")
    }
    attributes = copy.deepcopy(card.get("attributes") or {})
    protected_fields: dict[str, list[str]] = {}
    refreshed_ids = []
    for reference_id in requested_ids:
        previous = snapshots_by_id.get(reference_id)
        current = reference_snapshot_for_card(records_by_id[reference_id], card.get("type", "custom"), utc_now())
        if previous and reference_snapshot_changed(previous, records_by_id[reference_id]):
            attributes, protected = refresh_derived_attributes(attributes, previous, current)
            if protected:
                protected_fields[reference_id] = protected
            if card.get("type") != "character":
                for field, prior_value in (previous.get("derived_card_fields") or {}).items():
                    next_value = (current.get("derived_card_fields") or {}).get(field)
                    if card.get(field) == prior_value:
                        card[field] = next_value
                    elif card.get(field) != next_value:
                        protected_fields.setdefault(reference_id, []).append(field)
            refreshed_ids.append(reference_id)
            snapshots_by_id[reference_id] = current
        elif not previous:
            snapshots_by_id[reference_id] = current

    snapshots = [
        snapshots_by_id[reference_id]
        for reference_id in linked_ids
        if reference_id in snapshots_by_id
    ]
    updates = {
        "attributes": attributes,
        "reference_snapshots": snapshots,
        "updated_at": utc_now(),
    }
    for field in ("name", "description", "story", "language"):
        if field in card:
            updates[field] = card[field]
    after_card = copy.deepcopy(card)
    after_card.update(updates)
    updates["change_history"] = append_card_history(
        card.get("change_history", []),
        before_card,
        after_card,
        "manual",
        "reference_update",
        requested_ids,
    )
    await save_card_versioned(card, user.user_id, updates, body.version)
    return {
        "card": card_response(card),
        "updated_reference_ids": refreshed_ids,
        "protected_fields": protected_fields,
    }


@router.get("/cards/{card_id}/history")
async def card_history(card_id: str, user: User = Depends(get_current_user)):
    """Return the short, account-scoped audit trail for a card."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    history = card_history_view(card.get("change_history", []))
    return {
        "history": history,
        "can_undo": any(not entry.get("undone") for entry in history),
        "can_redo": any(entry.get("undone") for entry in history),
    }


@router.post("/cards/{card_id}/history/undo")
async def undo_card_change(
    card_id: str,
    body: CardVersionInput,
    user: User = Depends(get_current_user),
):
    """Undo the latest saved user or manual change without crossing accounts."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    history = copy.deepcopy(card.get("change_history") or [])
    target = next((entry for entry in reversed(history) if not entry.get("undone")), None)
    if not target:
        raise HTTPException(status_code=409, detail="Non ci sono modifiche da annullare")

    restored = apply_history_entry(card, target, "before")
    target["undone"] = True
    updates = {
        field: restored[field]
        for field in target.get("before", {})
        if field in restored
    }
    updates["change_history"] = history
    updates["updated_at"] = utc_now()
    await save_card_versioned(card, user.user_id, updates, body.version)
    return {
        "card": card_response(card),
        "history": card_history_view(history),
        "entry": card_history_view([target])[0],
    }


@router.post("/cards/{card_id}/history/redo")
async def redo_card_change(
    card_id: str,
    body: CardVersionInput,
    user: User = Depends(get_current_user),
):
    """Restore the most recently undone change while the redo branch is intact."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    history = copy.deepcopy(card.get("change_history") or [])
    target = next((entry for entry in history if entry.get("undone")), None)
    if not target:
        raise HTTPException(status_code=409, detail="Non ci sono modifiche da ripristinare")

    restored = apply_history_entry(card, target, "after")
    target["undone"] = False
    updates = {
        field: restored[field]
        for field in target.get("after", {})
        if field in restored
    }
    updates["change_history"] = history
    updates["updated_at"] = utc_now()
    await save_card_versioned(card, user.user_id, updates, body.version)
    return {
        "card": card_response(card),
        "history": card_history_view(history),
        "entry": card_history_view([target])[0],
    }


@router.delete("/cards/{card_id}")
async def delete_card(
    card_id: str,
    body: CardVersionInput,
    user: User = Depends(get_current_user),
):
    result = await db.cards.delete_one({
        "id": card_id,
        "user_id": user.user_id,
        "version": body.version,
    })
    if result.deleted_count == 0:
        current = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
        if current:
            raise HTTPException(
                status_code=409,
                detail="La scheda è stata modificata altrove. Ricaricala prima di eliminarla.",
            )
        raise HTTPException(status_code=404, detail="Carta non trovata")
    return {"ok": True}


@router.post("/cards/{card_id}/linked", response_model=List[Card])
async def create_linked_cards(
    card_id: str,
    body: LinkedCardInput,
    user: User = Depends(get_current_user),
):
    """Create printable rule cards from a character's selected references."""
    character = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not character:
        raise HTTPException(status_code=404, detail="Personaggio non trovato")
    if character.get("type") != "character":
        raise HTTPException(status_code=400, detail="Le carte collegate partono da un personaggio")

    persisted_ids = list(dict.fromkeys(character.get("reference_ids") or []))
    requested_ids = body.reference_ids or persisted_ids
    requested_ids = list(dict.fromkeys(requested_ids))
    if not requested_ids:
        raise HTTPException(status_code=400, detail="Il personaggio non ha riferimenti normativi selezionati")
    if not set(requested_ids).issubset(persisted_ids):
        raise HTTPException(status_code=400, detail="Puoi creare carte solo dai riferimenti già collegati al personaggio")

    records_by_id = {
        record["id"]: record
        for record in await private_reference_records(user.user_id)
        if record.get("id") in requested_ids
    }
    if len(records_by_id) != len(requested_ids):
        raise HTTPException(status_code=404, detail="Uno o più riferimenti normativi non sono più disponibili")
    if any(not reference_is_trusted(record) for record in records_by_id.values()):
        raise HTTPException(
            status_code=409,
            detail="I riferimenti da verificare non possono generare carte regolamentari.",
        )

    original_version = int(character.get("version", 0) or 0)
    original_updated_at = character.get("updated_at")
    await save_card_versioned(
        character,
        user.user_id,
        {"updated_at": utc_now()},
        body.version,
    )

    from schemas.cards import Card as CardModel
    created = []
    for reference_id in requested_ids:
        record = records_by_id[reference_id]
        payload = reference_to_card_payload(record)
        card = CardModel(
            user_id=user.user_id,
            type=payload["card_type"],
            name=payload["name"],
            description=payload["description"],
            story=payload["story"],
            language=payload["content_language"],
            attributes=payload["attributes"],
            reference_ids=[reference_id],
            rule_sources=[reference_rule_source(record)],
            source_refs=payload["source_refs"],
            reference_snapshots=[reference_snapshot_for_card(record, payload["card_type"], utc_now())],
        )
        created.append(card)

    try:
        await insert_cards_atomically(created)
    except Exception:
        rollback_updates = {"version": original_version}
        if original_updated_at is not None:
            rollback_updates["updated_at"] = original_updated_at
        try:
            await db.cards.update_one(
                {
                    "id": character["id"],
                    "user_id": user.user_id,
                    "version": original_version + 1,
                },
                {"$set": rollback_updates},
            )
            character.update(rollback_updates)
        except Exception:
            logger.exception("Failed to roll back character version after linked-card failure")
        raise

    return [card_response(card.model_dump()) for card in created]
