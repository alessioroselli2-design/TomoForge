"""Privacy-safe structural diagnostics for English 5e monster statblocks.

The diagnostic inspects OCR text in process memory and returns aggregate integer
counters only. It never returns or persists source text, titles, or free-form OCR
tokens. The module is diagnostic-only and does not change parser acceptance.
"""

from __future__ import annotations

import re


_SPELLJAMMER_CONTEXT_PHRASES = (
    "spelljammer",
    "wildspace",
    "astral sea",
    "air envelope",
    "spelljamming helm",
)

_MONSTER_METADATA_PHRASES = (
    "saving throws",
    "damage vulnerabilities",
    "damage resistances",
    "damage immunities",
    "condition immunities",
    "senses",
    "languages",
    "challenge",
    "proficiency bonus",
)


def _normalized(value: str) -> str:
    return " ".join((value or "").casefold().split())


def _signals(text: str) -> dict[str, bool]:
    normalized = _normalized(text)
    armor_class = "armor class" in normalized
    hit_points = "hit points" in normalized
    speed = bool(re.search(r"\bspeed\b", normalized))
    ability_header = all(
        re.search(rf"\b{token}\b", normalized)
        for token in ("str", "dex", "con", "int", "wis", "cha")
    )
    challenge_or_proficiency = (
        "challenge" in normalized or "proficiency bonus" in normalized
    )
    actions_heading = bool(
        re.search(
            r"(?im)^\s*(?:actions|bonus actions|reactions|legendary actions)\s*$",
            text or "",
        )
    )
    metadata = sum(phrase in normalized for phrase in _MONSTER_METADATA_PHRASES)
    spelljammer_context = any(
        phrase in normalized for phrase in _SPELLJAMMER_CONTEXT_PHRASES
    )
    core_pair = armor_class and hit_points
    core_triplet = core_pair and speed
    monster_like_bundle = core_triplet and ability_header and (
        challenge_or_proficiency or actions_heading or metadata >= 3
    )
    return {
        "armor_class": armor_class,
        "hit_points": hit_points,
        "speed": speed,
        "core_pair": core_pair,
        "core_triplet": core_triplet,
        "ability_header": ability_header,
        "challenge_or_proficiency": challenge_or_proficiency,
        "actions_heading": actions_heading,
        "metadata": metadata >= 3,
        "spelljammer_context": spelljammer_context,
        "monster_like_bundle": monster_like_bundle,
    }


def _record_on_pages(record: dict, pages: set[int]) -> bool:
    return any(
        isinstance(ref, dict)
        and ref.get("page") is not None
        and int(ref["page"]) in pages
        for ref in (record.get("source_refs") or [])
    )


def english_monster_structural_diagnostics(
    pages: list[tuple[int, str]],
    records: list[dict],
) -> dict[str, int]:
    """Return aggregate English-statblock diagnostics without source content."""

    page_signals = {page: _signals(text) for page, text in pages}
    monster_like_pages = {
        page
        for page, signals in page_signals.items()
        if signals["monster_like_bundle"]
    }

    other_records_with_core_pair = 0
    other_records_with_core_triplet = 0
    other_records_with_monster_like_bundle = 0
    for record in records:
        if str(record.get("reference_type") or "other") != "other":
            continue
        signals = _signals(str(record.get("full_text") or ""))
        other_records_with_core_pair += int(signals["core_pair"])
        other_records_with_core_triplet += int(signals["core_triplet"])
        other_records_with_monster_like_bundle += int(signals["monster_like_bundle"])

    return {
        "boos_structural_pages_evaluated": len(page_signals),
        "boos_structural_pages_with_armor_class": sum(
            int(signals["armor_class"]) for signals in page_signals.values()
        ),
        "boos_structural_pages_with_hit_points": sum(
            int(signals["hit_points"]) for signals in page_signals.values()
        ),
        "boos_structural_pages_with_speed": sum(
            int(signals["speed"]) for signals in page_signals.values()
        ),
        "boos_structural_pages_with_english_core_pair": sum(
            int(signals["core_pair"]) for signals in page_signals.values()
        ),
        "boos_structural_pages_with_english_core_triplet": sum(
            int(signals["core_triplet"]) for signals in page_signals.values()
        ),
        "boos_structural_pages_with_ability_header": sum(
            int(signals["ability_header"]) for signals in page_signals.values()
        ),
        "boos_structural_pages_with_challenge_or_proficiency": sum(
            int(signals["challenge_or_proficiency"])
            for signals in page_signals.values()
        ),
        "boos_structural_pages_with_actions_heading": sum(
            int(signals["actions_heading"]) for signals in page_signals.values()
        ),
        "boos_structural_pages_with_monster_metadata_bundle": sum(
            int(signals["metadata"]) for signals in page_signals.values()
        ),
        "boos_structural_pages_with_spelljammer_context": sum(
            int(signals["spelljammer_context"]) for signals in page_signals.values()
        ),
        "boos_structural_pages_with_monster_like_bundle": len(monster_like_pages),
        "boos_structural_other_records_with_english_core_pair": other_records_with_core_pair,
        "boos_structural_other_records_with_english_core_triplet": other_records_with_core_triplet,
        "boos_structural_other_records_with_monster_like_bundle": other_records_with_monster_like_bundle,
        "boos_structural_other_records_on_monster_like_pages": sum(
            1
            for record in records
            if str(record.get("reference_type") or "other") == "other"
            and _record_on_pages(record, monster_like_pages)
        ),
        "boos_structural_monster_records_on_monster_like_pages": sum(
            1
            for record in records
            if str(record.get("reference_type") or "other") == "monster"
            and _record_on_pages(record, monster_like_pages)
        ),
    }
