import asyncio
import logging
import uuid
from typing import Optional

from fastapi import HTTPException
from spell_library import (
    extract_spell_records,
    merge_spell_records,
    search_spell_records,
    spell_to_card_payload,
)
from reference_library import (
    reference_is_trusted,
    reference_review_reason,
    reference_review_state,
)

from core.config import SPELL_PDF_DIRECTORY, utc_now
from core.db import db as _singleton_db
from schemas.library import SpellImportResult

logger = logging.getLogger("tomeforge")


async def private_spell_records(user_id: str, *, db=None) -> list[dict]:
    """Load only one owner's catalogue; no unauthenticated route calls this."""
    _db = db if db is not None else _singleton_db
    collection = getattr(_db, "private_spells", None)
    if collection is None:
        return []
    try:
        return await collection.find({"user_id": user_id}).to_list(3000)
    except Exception as exc:
        if "private_spells" in str(exc):
            logger.warning("Private spell catalogue schema is not available yet")
            return []
        raise


async def find_private_spell(user_id: str, query: str, *, db=None) -> Optional[dict]:
    matches = search_spell_records(await private_spell_records(user_id, db=db), query, limit=20)
    return next((spell for spell in matches if reference_is_trusted(spell)), None)


async def import_private_spell_pdfs(user_id: str, *, db=None) -> SpellImportResult:
    """Import supplied PDFs into a single private owner's catalogue."""
    _db = db if db is not None else _singleton_db
    pdf_paths = sorted(SPELL_PDF_DIRECTORY.glob("*.pdf"))
    if not pdf_paths:
        raise HTTPException(status_code=404, detail="Nessun PDF degli incantesimi è disponibile per l'importazione")

    extracted_groups = await asyncio.gather(
        *(asyncio.to_thread(extract_spell_records, path) for path in pdf_paths)
    )
    records = merge_spell_records(record for group in extracted_groups for record in group)
    imported = updated = flagged = skipped = 0
    collection = getattr(_db, "private_spells", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Catalogo privato non disponibile")

    for record in records:
        if not record.get("name") or not record.get("description"):
            skipped += 1
            continue
        existing = await collection.find_one({
            "user_id": user_id,
            "normalized_name": record["normalized_name"],
        })
        payload = {
            **record,
            "user_id": user_id,
            "updated_at": utc_now(),
        }
        if existing:
            await collection.update_one({"id": existing["id"], "user_id": user_id}, {"$set": payload})
            updated += 1
        else:
            payload.update({"id": str(uuid.uuid4()), "imported_at": utc_now()})
            await collection.insert_one(payload)
            imported += 1
        flagged += bool(record.get("review_flags"))
    return SpellImportResult(
        imported=imported,
        updated=updated,
        flagged_for_review=flagged,
        skipped=skipped,
    )


def spell_summary(spell: dict) -> dict:
    """A compact result for the picker; full description is detail-only."""
    return {
        "id": spell["id"],
        "name": spell["name"],
        "level": spell.get("level", ""),
        "school": spell.get("school", ""),
        "classes": spell.get("classes", []),
        "casting_time": spell.get("casting_time", ""),
        "range": spell.get("range", ""),
        "source_refs": spell.get("source_refs", []),
        "review_status": spell.get("review_status", "pending"),
        "review_state": reference_review_state(spell),
        "is_trusted": reference_is_trusted(spell),
        "needs_review": not reference_is_trusted(spell),
        "review_reason": reference_review_reason(spell),
    }
