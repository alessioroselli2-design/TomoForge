from fastapi import HTTPException
from openai import AsyncOpenAI

from core.config import OPENAI_API_KEY, GEMINI_API_KEY, SEGMIND_API_KEY


def require_openai() -> AsyncOpenAI:
    api_key = (OPENAI_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenAI non configurato: aggiungi OPENAI_API_KEY")
    return AsyncOpenAI(api_key=api_key, timeout=120.0)


def require_segmind() -> str:
    api_key = (SEGMIND_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Segmind non configurato: aggiungi SEGMIND_API_KEY")
    return api_key


def require_gemini() -> str:
    api_key = (GEMINI_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini non configurato: aggiungi GEMINI_API_KEY")
    return api_key
