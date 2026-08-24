import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from core.auth import get_current_user
from core.config import MIME_TYPES
from core.db import db, get_db, get_object, SupabaseDatabase
from schemas.users import User
from services.media import save_file

router = APIRouter()


@router.post("/upload")
async def upload(file: UploadFile = File(...), user: User = Depends(get_current_user), db: SupabaseDatabase = Depends(get_db)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "png"
    content_type = MIME_TYPES.get(ext, file.content_type or "application/octet-stream")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Carica un file immagine valido")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="L'immagine supera il limite di 10 MB")
    path = f"uploads/{user.user_id}/{uuid.uuid4()}.{ext}"
    return {"artwork_path": await save_file(path, data, content_type, user.user_id, file.filename, db=db)}


@router.get("/files/{path:path}")
async def download(path: str, user: User = Depends(get_current_user), db: SupabaseDatabase = Depends(get_db)):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record or record["user_id"] != user.user_id:
        raise HTTPException(status_code=404, detail="File non trovato")
    return Response(content=get_object(path), media_type=record.get("content_type", "application/octet-stream"))
