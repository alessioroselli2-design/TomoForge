"""Conservative semantic identity matching for canonical records.

Decide only whether differently named records describe the same rule.
It never merges texts or chooses the canonical wording.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import math
import re
from difflib import SequenceMatcher
from hashlib import sha256
from typing import Any, Callable

import requests

from core.config import OPENAI_API_KEY, OPENAI_TEXT_MODEL
from reference_library import (
    normalize_reference_name,
    reference_content_fingerprint,
    reference_effective_level,
    reference_effective_type,
)


IdentityComparator = Callable[[dict, list[dict]], dict[str, Any]]

MATCH_MIN_CONFIDENCE = 0.92
NO_MATCH_MIN_CONFIDENCE = 0.95
MAX_IDENTITY_CANDIDATES = 6

# A high AI confidence is not sufficient on its own.
# Semantic identity matches must also be plausible according to
# the deterministic local candidate ranking.
MATCH_MIN_LOCAL_SCORE = 0.45
MATCH_MAX_BEST_SCORE_GAP = 0.10
MATCH_MAX_CANDIDATE_RANK = 3


def _tokens(value: str) -> set[str]:
    value = normalize_reference_name(value or "")
    return {token for token in re.split(r"\s+", value) if len(token) > 1}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _excerpt(record: dict, limit: int = 1800) -> str:
    value = str(
        record.get("full_text")
        or record.get("source_full_text")
        or record.get("description")
        or ""
    )
    return " ".join(value.split())[:limit]


def identity_name(record: dict) -> str:
    review = record.get("ai_review_corrections") or {}
    alias = str(review.get("identity_normalized_name") or "").strip()
    return alias or str(
        record.get("normalized_name")
        or normalize_reference_name(record.get("name", ""))
    )


def identity_is_resolved(record: dict) -> bool:
    review = record.get("ai_review_corrections") or {}
    return review.get("identity_status") in {"matched", "no_match", "exact"}


def _same_progression_slot(record: dict, candidate: dict) -> bool:
    reference_type = reference_effective_type(record)

    if reference_type != reference_effective_type(candidate):
        return False

    fields = []

    if reference_type in {"subclass", "class_feature", "ability"}:
        fields.append("parent_class")

    if reference_type in {"class_feature", "ability"}:
        fields.extend(["parent_subclass", "level"])

    if reference_type == "spell":
        fields.append("level")

    for field in fields:
        if field == "level":
            left = normalize_reference_name(
                reference_effective_level(record)
            )
            right = normalize_reference_name(
                reference_effective_level(candidate)
            )
        else:
            left = normalize_reference_name(
                str(record.get(field) or "")
            )
            right = normalize_reference_name(
                str(candidate.get(field) or "")
            )

        if left and right and left != right:
            return False

    return True


def identity_candidate_score(record: dict, candidate: dict) -> float:
    if record.get("id") == candidate.get("id"):
        return -1.0

    if record.get("user_id") != candidate.get("user_id"):
        return -1.0

    if (
        record.get("source_key")
        and record.get("source_key") == candidate.get("source_key")
    ):
        return -1.0

    if not _same_progression_slot(record, candidate):
        return -1.0

    left_name = normalize_reference_name(
        str(record.get("name") or record.get("normalized_name") or "")
    )
    right_name = normalize_reference_name(
        str(candidate.get("name") or candidate.get("normalized_name") or "")
    )

    name_ratio = (
        SequenceMatcher(None, left_name, right_name).ratio()
        if left_name and right_name
        else 0.0
    )

    name_tokens = _jaccard(_tokens(left_name), _tokens(right_name))

    left_text = _excerpt(record)
    right_text = _excerpt(candidate)

    content_overlap = _jaccard(_tokens(left_text), _tokens(right_text))

    if left_text and right_text:
        length_ratio = min(len(left_text), len(right_text)) / max(
            len(left_text), len(right_text)
        )
    else:
        length_ratio = 0.0

    score = (
        0.50 * name_ratio
        + 0.20 * name_tokens
        + 0.25 * content_overlap
        + 0.05 * length_ratio
    )

    if (
        candidate.get("source_language") in {"it", "en"}
        and candidate.get("translation_status") != "translated"
    ):
        score += 0.03

    return min(1.0, score)


def identity_candidates(
    record: dict,
    records: list[dict],
    limit: int = MAX_IDENTITY_CANDIDATES,
) -> list[dict]:
    scored = []

    for candidate in records:
        score = identity_candidate_score(record, candidate)

        if score < 0.18:
            continue

        scored.append((score, candidate))

    scored.sort(
        key=lambda item: (-item[0], str(item[1].get("id", "")))
    )

    return [
        candidate
        for _, candidate in scored[: max(1, limit)]
    ]


def identity_catalog_fingerprint(
    record: dict,
    candidates: list[dict],
) -> str:
    payload = [
        "identity-effective-type-v2",
        str(record.get("id", "")),
        reference_content_fingerprint(record),
        reference_effective_type(record),
        reference_effective_level(record),
    ]

    payload.extend(
        (
            f"{candidate.get('id', '')}:"
            f"{reference_content_fingerprint(candidate)}:"
            f"{reference_effective_type(candidate)}:"
            f"{reference_effective_level(candidate)}"
        )
        for candidate in sorted(
            candidates,
            key=lambda row: str(row.get("id", "")),
        )
    )

    return sha256("|".join(payload).encode("utf-8")).hexdigest()


def _prompt_record(record: dict) -> dict:
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


def openai_identity_comparator(
    record: dict,
    candidates: list[dict],
) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI identity comparator non configurato")

    payload = {
        "record": _prompt_record(record),
        "candidates": [
            _prompt_record(candidate)
            for candidate in candidates
        ],
    }

    prompt = (
        "Decidi se il record rappresenta ESATTAMENTE la stessa "
        "regola, privilegio, incantesimo o elemento di uno dei candidati. "
        "Titoli tradotti o sinonimi possono essere diversi, ma un argomento "
        "simile non basta. Non correggere il testo, non fondere record e non "
        "usare conoscenza esterna. "
        "Se nessun candidato rappresenta la stessa identità usa no_match. "
        "Se non sei sicuro usa uncertain. "
        "Per matched scegli soltanto un candidate_source_record_id fornito. "
        "Restituisci esclusivamente JSON: "
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
                        "Return strict JSON only. "
                        "Never force a semantic identity match."
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


async def _compare(
    comparator: IdentityComparator,
    record: dict,
    candidates: list[dict],
) -> dict[str, Any]:
    if inspect.iscoroutinefunction(comparator):
        result = comparator(record, candidates)
    else:
        result = await asyncio.to_thread(
            comparator,
            record,
            candidates,
        )

    return await result if inspect.isawaitable(result) else result


async def resolve_identity(
    record: dict,
    records: list[dict],
    *,
    comparator: IdentityComparator | None = None,
) -> dict[str, Any]:
    candidates = identity_candidates(record, records)

    catalog_fingerprint = identity_catalog_fingerprint(
        record,
        candidates,
    )

    if not candidates:
        return {
            "status": "uncertain",
            "identity_normalized_name": "",
            "matched_source_record_id": "",
            "confidence": 0.0,
            "notes": (
                "Nessun candidato locale sufficientemente simile; "
                "non è sicuro dichiarare che il record sia unico."
            ),
            "model": "candidate-prefilter",
            "catalog_fingerprint": catalog_fingerprint,
        }

    try:
        answer = await _compare(
            comparator or openai_identity_comparator,
            record,
            candidates,
        )

        if not isinstance(answer, dict):
            raise ValueError("identity comparator did not return an object")

        status = str(answer.get("status") or "uncertain")
        selected_id = str(
            answer.get("candidate_source_record_id") or ""
        )
        confidence = float(answer.get("confidence", 0))
        notes = str(answer.get("notes") or "")[:1200]

        if (
            not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("invalid identity confidence")

        valid_ids = {
            str(candidate.get("id"))
            for candidate in candidates
        }

        if status == "matched":
            if selected_id not in valid_ids:
                raise ValueError(
                    "identity comparator selected unknown candidate"
                )

            ranked_candidates = sorted(
                (
                    (
                        identity_candidate_score(record, candidate),
                        candidate,
                    )
                    for candidate in candidates
                ),
                key=lambda item: (
                    -item[0],
                    str(item[1].get("id", "")),
                ),
            )

            selected = next(
                candidate
                for candidate in candidates
                if str(candidate.get("id")) == selected_id
            )

            selected_score = identity_candidate_score(
                record,
                selected,
            )
            best_score = ranked_candidates[0][0]

            selected_rank = next(
                index
                for index, (_, candidate) in enumerate(
                    ranked_candidates,
                    1,
                )
                if str(candidate.get("id")) == selected_id
            )

            gate_reasons = []

            if selected_score < MATCH_MIN_LOCAL_SCORE:
                gate_reasons.append(
                    f"local_score={selected_score:.3f}"
                )

            if selected_rank > MATCH_MAX_CANDIDATE_RANK:
                gate_reasons.append(
                    f"candidate_rank={selected_rank}"
                )

            if (
                best_score - selected_score
                > MATCH_MAX_BEST_SCORE_GAP
            ):
                gate_reasons.append(
                    "too_far_from_best="
                    f"{best_score - selected_score:.3f}"
                )

            if confidence < MATCH_MIN_CONFIDENCE:
                status = "uncertain"
                selected_id = ""

            elif gate_reasons:
                status = "uncertain"
                selected_id = ""
                confidence = min(
                    confidence,
                    MATCH_MIN_CONFIDENCE - 0.01,
                )
                gate_note = (
                    "Match AI non accettato dal controllo "
                    "deterministico: "
                    + ", ".join(gate_reasons)
                )
                notes = (
                    f"{notes} | {gate_note}"
                    if notes
                    else gate_note
                )[:1200]

        elif status == "no_match":
            selected_id = ""

            if confidence < NO_MATCH_MIN_CONFIDENCE:
                status = "uncertain"

        elif status == "uncertain":
            selected_id = ""

        else:
            raise ValueError("invalid identity status")

    except Exception as exc:
        return {
            "status": "uncertain",
            "identity_normalized_name": "",
            "matched_source_record_id": "",
            "confidence": 0.0,
            "notes": (
                "Identity comparator unavailable or invalid: "
                f"{type(exc).__name__}"
            ),
            "model": OPENAI_TEXT_MODEL,
            "catalog_fingerprint": catalog_fingerprint,
        }

    alias = ""

    if status == "matched":
        selected = next(
            candidate
            for candidate in candidates
            if str(candidate.get("id")) == selected_id
        )

        alias = identity_name(selected)

    return {
        "status": status,
        "identity_normalized_name": alias,
        "matched_source_record_id": (
            selected_id if status == "matched" else ""
        ),
        "confidence": confidence,
        "notes": notes,
        "model": OPENAI_TEXT_MODEL,
        "catalog_fingerprint": catalog_fingerprint,
    }
