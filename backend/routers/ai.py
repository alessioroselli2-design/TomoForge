import asyncio
import base64
import json
import logging
import uuid

import requests
from fastapi import APIRouter, Depends, HTTPException
from reference_library import reference_to_card_payload
from spell_library import spell_to_card_payload

from core.auth import require_premium
from core.config import GEMINI_TEXT_MODEL, MOCK_DATA, SEGMIND_IMAGE_MODEL
from core.providers import require_gemini, require_segmind
from schemas.ai import GenerateContentInput, GenerateImageInput
from schemas.users import User
from services.ai import LANGUAGES, TYPE_LABELS, TYPE_SCHEMAS, parse_ai_json
from services.library import find_private_reference
from services.media import save_artwork, save_file
from services.spells import find_private_spell

router = APIRouter()
logger = logging.getLogger("tomeforge")


@router.post("/ai/generate-content")
async def generate_content(body: GenerateContentInput, user: User = Depends(require_premium)):
    if MOCK_DATA:
        return {
            "name": "Eco della Luna (Demo)",
            "description": f"Una creazione simulata per: {body.prompt}.",
            "story": "Il testo dimostrativo appare senza chiamare OpenAI.",
            "attributes": {"livello": "2", "scuola": "Illusione", "azione": "1 azione", "danno": "2d6 psichico"},
            "source": "ai_generated",
            "source_status": "unavailable",
            "source_message": "Nessuna fonte verificata è disponibile nella biblioteca: questo è contenuto dimostrativo.",
        }
    if body.type == "spell":
        spell = await find_private_spell(user.user_id, body.prompt)
        if spell:
            return spell_to_card_payload(spell)
    reference = await find_private_reference(user.user_id, body.prompt, body.type)
    if reference:
        return reference_to_card_payload(reference)
    language = LANGUAGES.get(body.language, "Italiano")
    type_label = body.custom_type if body.type == "custom" and body.custom_type else TYPE_LABELS.get(body.type, body.type)
    prompt = (
        f"Create a balanced Dungeons & Dragons 5e {type_label} card in {language} from: {body.prompt}. "
        f"Return only valid JSON with name, description (maximum 3 sentences), story (maximum 4 sentences), and {TYPE_SCHEMAS.get(body.type, TYPE_SCHEMAS['custom'])}."
    )
    try:
        response = await asyncio.to_thread(
            requests.post,
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TEXT_MODEL}:generateContent",
            headers={
                "x-goog-api-key": require_gemini(),
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"parts": [{
                    "text": (
                        "You are a D&D 5e content designer. Be accurate, imaginative, "
                        "and return JSON only.\n\n" + prompt
                    ),
                }]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.7,
                },
            },
            timeout=(10, 120),
        )
        response.raise_for_status()
        response_data = response.json()
        data = parse_ai_json(
            response_data["candidates"][0]["content"]["parts"][0]["text"]
        )
        return {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "story": data.get("story", ""),
            "attributes": data.get("attributes", {}),
            "source": "ai_generated",
            "source_status": "unavailable",
            "source_message": "Il contenuto richiesto non è disponibile come fonte verificata nella tua biblioteca; il testo generato non è una regola certa.",
        }
    except HTTPException:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Gemini ha restituito un formato non valido") from exc
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Gemini ha raggiunto il limite gratuito temporaneo. Riprova più tardi.",
            ) from exc
        logger.exception("Gemini content generation failed")
        raise HTTPException(status_code=502, detail="Errore nella generazione testo Gemini") from exc
    except Exception as exc:
        logger.exception("Gemini content generation failed")
        raise HTTPException(status_code=502, detail="Errore nella generazione testo Gemini") from exc


@router.post("/ai/generate-image")
async def generate_image(body: GenerateImageInput, user: User = Depends(require_premium)):
    if MOCK_DATA:
        demo_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        path = f"artwork/{user.user_id}/{uuid.uuid4()}.png"
        return {"artwork_path": await save_file(path, demo_png, "image/png", user.user_id, "mock-generated.png")}
    type_hint = TYPE_LABELS.get(body.type or "", "")
    prompt = (
        f"Create one art-only dark fantasy illustration depicting: {body.prompt}. "
        f"{'Subject category: ' + type_hint + '. ' if type_hint else ''}"
        "Detailed digital painting, dramatic lighting, obsidian, antique gold and crimson palette, portrait orientation. "
        "This is not a card design, cover, poster, sign, scroll, banner, or interface. "
        "Treat any names in the subject as internal character or place names only; never render them as writing. "
        "Absolutely no typography, words, letters, numbers, readable runes, glyphs, captions, signatures, watermarks, borders, frames, or labels."
    )
    try:
        response = await asyncio.to_thread(
            requests.post,
            f"https://api.segmind.com/v1/{SEGMIND_IMAGE_MODEL}",
            headers={"x-api-key": require_segmind(), "Content-Type": "application/json"},
            json={
                "prompt": prompt,
                "samples": 1,
                "guidance": 3.5,
                "steps": 25,
                "prompt_strength": 0.8,
                "aspect_ratio": "2:3",
                "output_format": "webp",
                "output_quality": 85,
            },
            timeout=(10, 120),
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type.startswith("image/"):
            artwork_data = response.content
        else:
            payload = response.json()
            image_value = payload.get("image") or payload.get("output") or payload.get("url")
            if isinstance(image_value, list):
                image_value = image_value[0] if image_value else None
            if not isinstance(image_value, str) or not image_value:
                raise ValueError("Segmind did not return image data")
            if image_value.startswith(("https://", "http://")):
                image_response = await asyncio.to_thread(requests.get, image_value, timeout=(10, 120))
                image_response.raise_for_status()
                artwork_data = image_response.content
                content_type = image_response.headers.get("content-type", "image/jpeg").split(";", 1)[0].lower()
            else:
                artwork_data = base64.b64decode(image_value.split(",", 1)[-1])
                content_type = "image/png"
        if not artwork_data or not content_type.startswith("image/"):
            raise ValueError("Segmind did not return a usable image")
        extension = {"image/jpeg": "jpg", "image/webp": "webp", "image/png": "png"}.get(content_type, "png")
        path = f"artwork/{user.user_id}/{uuid.uuid4()}.{extension}"
        artwork_path, cleanup_notice = await save_artwork(
            path,
            artwork_data,
            content_type,
            user.user_id,
            f"segmind-generated.{extension}",
            cleanup=body.cleanup,
        )
        result = {"artwork_path": artwork_path}
        if cleanup_notice:
            result["cleanup_notice"] = cleanup_notice
        return result
    except HTTPException:
        raise
    except requests.RequestException as exc:
        logger.exception("Segmind image generation failed")
        raise HTTPException(status_code=502, detail="Segmind non ha potuto generare l'immagine") from exc
    except Exception as exc:
        logger.exception("Segmind image processing failed")
        raise HTTPException(status_code=502, detail="Segmind ha restituito un'immagine non valida") from exc
