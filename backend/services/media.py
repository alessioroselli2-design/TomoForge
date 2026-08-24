import asyncio
import base64
import io
import logging
import uuid
from pathlib import Path
from typing import Optional

import requests

from core.config import (
    ARTWORK_CLEANUP_ENABLED, ARTWORK_CLEANUP_MODEL,
    MOCK_DATA, OPENAI_API_KEY, utc_now,
)
from core.db import db as _singleton_db, put_object
from core.providers import require_openai

logger = logging.getLogger("tomeforge")


async def save_file(path: str, data: bytes, content_type: str, user_id: str, original_filename: Optional[str] = None, *, db=None) -> str:
    _db = db if db is not None else _singleton_db
    stored_path = put_object(path, data, content_type)
    await _db.files.insert_one({
        "id": str(uuid.uuid4()), "storage_path": stored_path, "user_id": user_id,
        "original_filename": original_filename, "content_type": content_type,
        "is_deleted": False, "created_at": utc_now(),
    })
    return stored_path


ARTWORK_CLEANUP_PROMPT = (
    "Clean this artwork before it is saved. Remove any visible decorative signature, "
    "watermark, logo, artist mark, text, letters, numbers, or readable glyphs that may "
    "have been added by the image model. Preserve the original subject, pose, composition, "
    "lighting, colors, and portrait aspect ratio. Do not add any new writing or change the "
    "artwork into a card, poster, cover, banner, or interface. Return only the cleaned artwork."
)


def _artwork_input_filename(content_type: str) -> str:
    extension = {
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
    }.get(content_type, "png")
    return f"artwork.{extension}"


async def cleanup_artwork(data: bytes, content_type: str) -> tuple[bytes, str]:
    """Remove model-added marks before artwork reaches storage."""
    if not ARTWORK_CLEANUP_ENABLED:
        return data, content_type
    if not data or not content_type.startswith("image/"):
        raise ValueError("Cannot clean an empty or non-image artwork")

    client = require_openai()
    image_file = io.BytesIO(data)
    image_file.name = _artwork_input_filename(content_type)
    response = await client.images.edit(
        model=ARTWORK_CLEANUP_MODEL,
        image=image_file,
        prompt=ARTWORK_CLEANUP_PROMPT,
    )
    result = response.data[0] if response.data else None
    image_value = result.get("b64_json") if isinstance(result, dict) else getattr(result, "b64_json", None)
    if image_value:
        cleaned_data = base64.b64decode(image_value)
        return cleaned_data, "image/png"

    image_url = result.get("url") if isinstance(result, dict) else getattr(result, "url", None)
    if image_url:
        image_response = await asyncio.to_thread(requests.get, image_url, timeout=(10, 120))
        image_response.raise_for_status()
        cleaned_content_type = image_response.headers.get("content-type", "image/png").split(";", 1)[0].lower()
        if not cleaned_content_type.startswith("image/"):
            raise ValueError("OpenAI cleanup did not return an image")
        return image_response.content, cleaned_content_type

    raise ValueError("OpenAI cleanup did not return image data")


def require_artwork_cleanup() -> None:
    """Confirm that the optional cleanup pass can run for this request."""
    from fastapi import HTTPException
    if not ARTWORK_CLEANUP_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="La pulizia opzionale di firme e filigrane non è disponibile su questo server.",
        )
    if MOCK_DATA:
        raise HTTPException(
            status_code=503,
            detail="La pulizia opzionale di firme e filigrane non è disponibile nella modalità demo.",
        )
    if not (OPENAI_API_KEY or "").strip():
        raise HTTPException(
            status_code=503,
            detail="La pulizia opzionale di firme e filigrane non è configurata su questo server.",
        )


async def save_artwork(
    path: str,
    data: bytes,
    content_type: str,
    user_id: str,
    original_filename: Optional[str] = None,
    *,
    cleanup: bool = False,
    db=None,
) -> tuple[str, Optional[str]]:
    """Validate and persist generated artwork, optionally cleaning model-added marks."""
    cleanup_notice = None
    if cleanup:
        try:
            require_artwork_cleanup()
            data, content_type = await cleanup_artwork(data, content_type)
        except Exception as exc:
            logger.warning("Artwork cleanup skipped; preserving original artwork: %s", exc)
            cleanup_notice = "Artwork generato, ma la pulizia di firme e filigrane non è riuscita. L'immagine originale è stata salvata."
        else:
            if not data or not content_type.startswith("image/"):
                from fastapi import HTTPException
                raise HTTPException(status_code=502, detail="La pulizia non ha restituito un'immagine valida")

    extension = {
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/png": "png",
    }.get(content_type, "png")
    if cleanup and not cleanup_notice:
        path = f"{path.rsplit('.', 1)[0]}.{extension}" if "." in path.rsplit("/", 1)[-1] else f"{path}.{extension}"
    if cleanup and not cleanup_notice and original_filename:
        cleaned_filename = f"{Path(original_filename).stem}.{extension}"
    else:
        cleaned_filename = original_filename or f"generated.{extension}"
    return await save_file(path, data, content_type, user_id, cleaned_filename, db=db), cleanup_notice
