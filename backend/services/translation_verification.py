"""Conservative AI verification for localized reference text.

This layer answers one question only: does the Italian localization faithfully
represent the immutable source snapshot? It never decides which rule source is
canonical, never repairs content, and never overrides OCR/source uncertainty.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import math
import re
from hashlib import sha256
from typing import Any, Callable

import requests

from core.config import OPENAI_API_KEY, OPENAI_TEXT_MODEL, utc_now
from services.reference_translation import normalize_language, translation_required

TRANSLATION_AI_VERIFIED = "ai_verified"
TRANSLATION_CONFLICT = "conflict"
TRANSLATION_LOW_CONFIDENCE = "low_confidence"
TRANSLATION_FAILED = "failed"
TRANSLATION_NOT_REQUIRED = "not_required"
TRANSLATION_PENDING = "pending"
TRANSLATION_VERIFIED_MIN_CONFIDENCE = 0.97

TranslationComparator = Callable[[dict], dict[str, Any]]

_DICE_RE = re.compile(r"(?<![\w])\d+d\d+(?:\s*[+-]\s*\d+)?(?![\w])", re.IGNORECASE)
_NUMBER_RE = re.compile(r"(?<![\w])(?:\d+(?:[.,]\d+)?%?|[+-]\d+)(?![\w])")


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def mechanical_tokens(text: str) -> tuple[str, ...]:
    """Stable numeric/dice tokens a faithful translation must not silently alter."""
    value = _clean(text).casefold()
    dice = [re.sub(r"\s+", "", token) for token in _DICE_RE.findall(value)]
    # Remove numbers already contained in dice expressions before collecting
    # standalone values, so `1d6` does not become an artificial 1/6 pair.
    without_dice = _DICE_RE.sub(" ", value)
    numbers = [token.replace(",", ".") for token in _NUMBER_RE.findall(without_dice)]
    return tuple(sorted(dice + numbers))


def translation_verification_fingerprint(record: dict) -> str:
    """Invalidate a prior verdict when either source or localized text changes."""
    payload = {
        "source_language": normalize_language(record.get("source_language")),
        "source_name": _clean(record.get("source_name")),
        "source_description": _clean(record.get("source_description")),
        "source_full_text": _clean(record.get("source_full_text")),
        "source_attributes": record.get("source_attributes") or {},
        "name": _clean(record.get("name")),
        "description": _clean(record.get("description")),
        "full_text": _clean(record.get("full_text")),
        "attributes": record.get("attributes") or {},
        "translation_status": str(record.get("translation_status") or "not_required"),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def translation_verification_required(record: dict) -> bool:
    return (
        translation_required(record.get("source_language"))
        and record.get("translation_status") == "translated"
    )


def translation_verification_is_current(record: dict) -> bool:
    stored = str(record.get("translation_review_fingerprint") or "")
    return bool(stored) and stored == translation_verification_fingerprint(record)


def _prompt_payload(record: dict) -> dict:
    return {
        "source_language": normalize_language(record.get("source_language")),
        "source": {
            "name": record.get("source_name", ""),
            "description": record.get("source_description", ""),
            "full_text": record.get("source_full_text", ""),
            "attributes": record.get("source_attributes") or {},
        },
        "italian_translation": {
            "name": record.get("name", ""),
            "description": record.get("description", ""),
            "full_text": record.get("full_text", ""),
            "attributes": record.get("attributes") or {},
        },
        # Source extraction uncertainty is deliberately visible to the model but
        # is not something this verifier may resolve.
        "source_review_flags": list(record.get("review_flags") or []),
    }


def build_translation_verification_prompt(record: dict) -> str:
    return (
        "Verifica esclusivamente la fedeltà della traduzione italiana rispetto al testo sorgente "
        "fornito. Non usare conoscenze esterne di D&D, non correggere la regola, non scegliere una "
        "fonte canonica e non inventare testo. Confronta nome, descrizione, full_text e attributes. "
        "Numeri, dadi, formule, bonus, percentuali e significato meccanico devono essere preservati. "
        "Differenze puramente linguistiche sono accettabili. I source_review_flags descrivono "
        "incertezze dell'estrazione e NON possono essere risolti da questa verifica di traduzione. "
        "Restituisci esclusivamente JSON nel formato "
        "{\"status\":\"verified|conflict|low_confidence\",\"confidence\":0.0," 
        "\"conflict_fields\":[\"...\"],\"notes\":\"...\"}. "
        "Usa conflict se la traduzione omette, aggiunge o altera contenuto; low_confidence se non "
        "puoi stabilire la fedeltà con sicurezza.\n\n"
        + json.dumps(_prompt_payload(record), ensure_ascii=False, separators=(",", ":"))
    )


def openai_translation_comparator(record: dict) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI translation verifier non configurato")
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_TEXT_MODEL,
            "messages": [
                {"role": "system", "content": "Return strict JSON only."},
                {"role": "user", "content": build_translation_verification_prompt(record)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        },
        timeout=(10, 90),
    )
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


async def _compare(comparator: TranslationComparator, record: dict) -> dict[str, Any]:
    if inspect.iscoroutinefunction(comparator):
        result = comparator(record)
    else:
        result = await asyncio.to_thread(comparator, record)
    return await result if inspect.isawaitable(result) else result


def _result(record: dict, status: str, confidence: float, notes: str, conflicts: list[str], model: str) -> dict:
    return {
        "status": status,
        "confidence": confidence,
        "notes": notes,
        "conflict_fields": conflicts,
        "model": model,
        "fingerprint": translation_verification_fingerprint(record),
        "reviewed_at": utc_now(),
    }


async def verify_translation(
    record: dict,
    comparator: TranslationComparator | None = None,
    *,
    model: str | None = None,
) -> dict:
    """Verify localization fidelity without changing the supplied record."""
    if not translation_required(record.get("source_language")):
        return _result(record, TRANSLATION_NOT_REQUIRED, 1.0, "Italian source; translation verification not required.", [], "")
    if record.get("translation_status") != "translated":
        return _result(
            record,
            TRANSLATION_PENDING,
            0.0,
            f"Translation is not ready: {record.get('translation_status') or 'unknown'}.",
            ["translation_status"],
            "",
        )

    if not _clean(record.get("source_name")) or not _clean(record.get("source_full_text")):
        return _result(record, TRANSLATION_CONFLICT, 1.0, "Immutable source snapshot is incomplete.", ["source_snapshot"], "deterministic")
    if not _clean(record.get("name")) or not _clean(record.get("full_text")):
        return _result(record, TRANSLATION_CONFLICT, 1.0, "Italian translation is incomplete.", ["translation"], "deterministic")

    source_tokens = mechanical_tokens(
        f"{record.get('source_name', '')} {record.get('source_description', '')} {record.get('source_full_text', '')}"
    )
    translated_tokens = mechanical_tokens(
        f"{record.get('name', '')} {record.get('description', '')} {record.get('full_text', '')}"
    )
    if source_tokens != translated_tokens:
        return _result(
            record,
            TRANSLATION_CONFLICT,
            1.0,
            "Mechanical numeric/dice tokens differ between source and translation.",
            ["mechanical_tokens"],
            "deterministic",
        )

    selected_model = model or OPENAI_TEXT_MODEL
    try:
        answer = await _compare(comparator or openai_translation_comparator, record)
        if not isinstance(answer, dict):
            raise ValueError("AI returned a non-object verdict")
        raw_status = str(answer.get("status") or "").strip().casefold()
        if raw_status not in {"verified", "conflict", "low_confidence"}:
            raise ValueError("AI returned an invalid translation status")
        confidence = float(answer.get("confidence", 0))
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("AI returned an invalid confidence")
        conflicts = answer.get("conflict_fields") or []
        if not isinstance(conflicts, list) or any(not isinstance(field, str) for field in conflicts):
            raise ValueError("AI returned invalid conflict fields")
        notes = _clean(answer.get("notes"))

        if raw_status == "verified":
            status = (
                TRANSLATION_AI_VERIFIED
                if confidence >= TRANSLATION_VERIFIED_MIN_CONFIDENCE
                else TRANSLATION_LOW_CONFIDENCE
            )
            if status == TRANSLATION_LOW_CONFIDENCE and not conflicts:
                conflicts = ["translation_fidelity"]
        elif raw_status == "conflict":
            status = TRANSLATION_CONFLICT if confidence >= 0.75 else TRANSLATION_LOW_CONFIDENCE
            if not conflicts:
                conflicts = ["translation_fidelity"]
        else:
            status = TRANSLATION_LOW_CONFIDENCE
            if not conflicts:
                conflicts = ["translation_fidelity"]

        return _result(record, status, confidence, notes, conflicts, selected_model)
    except Exception as exc:
        return _result(
            record,
            TRANSLATION_FAILED,
            0.0,
            f"Translation verifier failed: {type(exc).__name__}.",
            ["translation_verifier"],
            selected_model,
        )
