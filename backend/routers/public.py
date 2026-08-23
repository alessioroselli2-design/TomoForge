from fastapi import APIRouter, HTTPException, Response

from core.db import db, get_object

router = APIRouter()


@router.get("/public/cards/{card_id}")
async def public_get_card(card_id: str):
    card = await db.cards.find_one({"id": card_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    public_fields = (
        "id", "type", "custom_type", "name", "description", "story", "language",
        "attributes", "artwork_path", "frame", "appearance", "back",
    )
    return {field: card[field] for field in public_fields if field in card}


@router.get("/public/files/{path:path}")
async def public_download(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File non trovato")
    return Response(content=get_object(path), media_type=record.get("content_type", "application/octet-stream"))
