"""Two-pass consensus for semantic identity matching.

The first pass uses the normal identity resolver. Only a locally-gated AI match
is sent to a second, stricter verifier. No database writes happen here.
"""
from __future__ import annotations

import json
from typing import Any

import requests

from core.config import OPENAI_API_KEY, OPENAI_TEXT_MODEL
from reference_library import (
    reference_effective_level,
    reference_effective_type,
)
from services.canonical_identity import IdentityComparator, resolve_identity

CONSENSUS_UNCERTAIN_CONFIDENCE_CAP = 0.91


def _excerpt(record: dict, limit: int = 1800) -> str:
    value = str(
        record.get("full_text")
        or record.get("source_full_text")
        or record.get("description")
        or ""
    )
    return " ".join(value.split())[:limit]


def _prompt_record(record: dict) -> dict[str, Any]:
    return {
        "source_record_id": record.get("id"),
        "reference_type": reference_effective_type(record),
        "source_reference_type": record.get("reference_type"),
        "name": record.get("name"),
        "normalized_name": record.get("normalized_name"),
        "source_name": record.get("source_name"),
        "parent_class": record.get("parent_class"),
        "parent_subclass": record.get("parent_subclass"),
        "level": reference_effective_level(record),
        "source_language": record.get("source_language"),
        "translation_status": record.get("translation_status"),
        "text_excerpt": _excerpt(record),
        "attributes": record.get("attributes") or {},
    }


def strict_openai_identity_verifier(
    record: dict,
    candidates: list[dict],
) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI identity verifier non configurato")

    payload = {
        "record": _prompt_record(record),
        "candidates": [
            _prompt_record(candidate)
            for candidate in candidates
        ],
    }

    prompt = (
        "Sei il SECONDO verificatore indipendente e scettico. "
        "Valuta soltanto i dati forniti, senza conoscenza esterna. "
        "Un match è valido solo se record e candidato rappresentano "
        "la stessa identità di regola o elemento, con meccanica, "
        "contesto e ruolo compatibili. Somiglianza di tema, parole "
        "condivise o categorie vicine NON bastano. "
        "Se esiste una differenza materiale usa no_match. "
        "Se i dati non bastano usa uncertain. "
        "Non correggere e non fondere testi. "
        "Per matched scegli esclusivamente un "
        "candidate_source_record_id fornito. "
        "Restituisci solo JSON: "
        '{"status":"matched|no_match|uncertain",'
        '"candidate_source_record_id":"id oppure stringa vuota",'
        '"confidence":0.0,"notes":"breve motivo"}.\n'
        + json.dumps(payload, ensure_ascii=False)
    )

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_TEXT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON only. Be skeptical. "
                        "Never confirm a match from topical "
                        "similarity alone."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        },
        timeout=(10, 90),
    )

    response.raise_for_status()

    return json.loads(
        response.json()["choices"][0]["message"]["content"]
    )


async def resolve_identity_consensus(
    record: dict,
    records: list[dict],
    *,
    first_comparator: IdentityComparator | None = None,
    second_comparator: IdentityComparator | None = None,
) -> dict[str, Any]:
    """
    Accetta un alias solo con doppia conferma.

    La seconda chiamata viene eseguita soltanto quando la prima
    passa già tutti i controlli del resolver normale.
    Ogni disaccordo fallisce in sicurezza come uncertain.
    """
    first = await resolve_identity(
        record,
        records,
        comparator=first_comparator,
    )

    if first.get("status") != "matched":
        return {
            **first,
            "consensus": "not_required",
            "consensus_passes": 1,
        }

    second = await resolve_identity(
        record,
        records,
        comparator=(
            second_comparator
            or strict_openai_identity_verifier
        ),
    )

    first_id = str(
        first.get("matched_source_record_id") or ""
    )
    second_id = str(
        second.get("matched_source_record_id") or ""
    )

    fingerprints_match = (
        first.get("catalog_fingerprint")
        == second.get("catalog_fingerprint")
    )

    if (
        fingerprints_match
        and second.get("status") == "matched"
        and first_id
        and first_id == second_id
    ):
        return {
            **first,
            "confidence": min(
                float(first.get("confidence", 0)),
                float(second.get("confidence", 0)),
            ),
            "notes": (
                "Consensus 2/2 confermato. "
                f"Prima: {first.get('notes', '')} | "
                f"Seconda: {second.get('notes', '')}"
            )[:1200],
            "consensus": "confirmed",
            "consensus_passes": 2,
        }

    details = (
        f"Prima={first.get('status')}:{first_id or '-'}; "
        f"Seconda={second.get('status')}:{second_id or '-'}; "
        "fingerprint="
        f"{'ok' if fingerprints_match else 'changed'}"
    )

    return {
        **first,
        "status": "uncertain",
        "identity_normalized_name": "",
        "matched_source_record_id": "",
        "confidence": min(
            float(first.get("confidence", 0)),
            float(second.get("confidence", 0)),
            CONSENSUS_UNCERTAIN_CONFIDENCE_CAP,
        ),
        "notes": (
            f"Consensus non raggiunto: {details}"
        )[:1200],
        "consensus": "disagreed",
        "consensus_passes": 2,
    }
