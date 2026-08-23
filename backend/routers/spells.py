from fastapi import APIRouter, Depends, HTTPException, Query
from reference_library import reference_is_trusted, reference_review_reason
from spell_library import spell_to_card_payload

from core.auth import get_current_user, require_admin
from core.db import db
from schemas.library import SpellImportResult
from schemas.users import User
from services.spells import (
    import_private_spell_pdfs,
    private_spell_records,
    spell_summary,
)

import logging

logger = logging.getLogger("tomeforge")

router = APIRouter()


@router.get("/spells")
async def search_private_spells(
    q: str = Query("", max_length=120),
    review_only: bool = False,
    user: User = Depends(get_current_user),
):
    from spell_library import search_spell_records
    records = search_spell_records(await private_spell_records(user.user_id), q)
    if review_only:
        records = [record for record in records if record.get("review_flags")]
    return {"spells": [spell_summary(record) for record in records]}


@router.post("/spells/import", response_model=SpellImportResult)
async def import_private_spells(user: User = Depends(require_admin)):
    """Admin-only local import; it never copies the PDF binaries to storage."""
    try:
        return await import_private_spell_pdfs(user.user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Private spell PDF import failed")
        raise HTTPException(status_code=502, detail="Importazione del Grimorio non riuscita") from exc


@router.get("/spells/{spell_id}")
async def get_private_spell(spell_id: str, user: User = Depends(get_current_user)):
    spell = await db.private_spells.find_one({"id": spell_id, "user_id": user.user_id})
    if not spell:
        raise HTTPException(status_code=404, detail="Incantesimo non trovato nel tuo Grimorio")
    return spell_summary(spell)


@router.post("/spells/{spell_id}/apply")
async def apply_private_spell(spell_id: str, user: User = Depends(get_current_user)):
    spell = await db.private_spells.find_one({"id": spell_id, "user_id": user.user_id})
    if not spell:
        raise HTTPException(status_code=404, detail="Incantesimo non trovato nel tuo Grimorio")
    if not reference_is_trusted(spell):
        raise HTTPException(
            status_code=409,
            detail=reference_review_reason(spell) or "Questo incantesimo è da verificare e non può essere usato come dato certo.",
        )
    return {**spell_to_card_payload(spell), "spell_id": spell["id"]}
