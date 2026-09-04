"""Conservative parser for D&D 5e monster stat blocks extracted by OCR.

This parser is intentionally separate from the generic heading/table parser.
Monster pages have dense two-column stat blocks whose attack rows look like
weapons to a generic document parser.  A candidate is accepted only when a
size/type descriptor is immediately followed by the core armor/HP/speed
stat-block markers.  Callers should still require independent OCR agreement
before persisting any candidate.
"""

from __future__ import annotations

import re
from hashlib import sha256
from typing import Iterable

from reference_library import clean_text, compact_text, normalize_reference_name

_SIZE_WORDS = (
    "minuscolo",
    "piccolo",
    "medio",
    "grande",
    "enorme",
    "mastodontico",
)

_CREATURE_TYPE_WORDS = (
    "aberrazione",
    "bestia",
    "celestiale",
    "costrutto",
    "drago",
    "elementale",
    "folletto",
    "gigante",
    "immondo",
    "melma",
    "mostruosità",
    "mostruosita",
    "non morto",
    "non-morto",
    "pianta",
    "umanoide",
)

_STRUCTURAL_PREFIXES = (
    "classe armatura",
    "punti ferita",
    "velocità",
    "velocita",
    "for ",
    "des ",
    "cos ",
    "int ",
    "sag ",
    "car ",
    "tiri salvezza",
    "abilità",
    "abilita",
    "vulnerabilità",
    "vulnerabilita",
    "resistenze",
    "immunità",
    "immunita",
    "sensi",
    "linguaggi",
    "grado di sfida",
    "azioni",
    "reazioni",
    "azioni leggendarie",
    "azioni di tana",
)


def _norm(value: str) -> str:
    return normalize_reference_name(clean_text(value or ""))


def _line_is_descriptor(line: str) -> bool:
    value = _norm(line)
    return (
        any(re.search(rf"\b{re.escape(size)}\b", value) for size in _SIZE_WORDS)
        and any(creature_type in value for creature_type in _CREATURE_TYPE_WORDS)
        and len(value) <= 180
    )


def _line_is_title_candidate(line: str) -> bool:
    raw = clean_text(line or "").strip(" .:;,—–-")
    if not 2 <= len(raw) <= 80 or not any(ch.isalpha() for ch in raw):
        return False
    normalized = _norm(raw)
    if not normalized:
        return False
    if any(normalized.startswith(prefix) for prefix in _STRUCTURAL_PREFIXES):
        return False
    if _line_is_descriptor(raw):
        return False
    # A monster title is normally a short heading.  Avoid narrative lines that
    # happen to precede a descriptor because OCR column order can interleave text.
    words = normalized.split()
    if len(words) > 8:
        return False
    letters = [ch for ch in raw if ch.isalpha()]
    upper_ratio = sum(ch.isupper() for ch in letters) / max(len(letters), 1)
    titleish_ratio = sum(word[:1].isupper() for word in raw.split() if word) / max(len(raw.split()), 1)
    return upper_ratio >= 0.62 or titleish_ratio >= 0.7


def _core_anchor(line: str) -> bool:
    value = _norm(line)
    return value.startswith("classe armatura") or value.startswith("classe d armatura")


def _marker_near(lines: list[str], anchor_index: int, marker: str, lookahead: int = 8) -> bool:
    marker_norm = _norm(marker)
    for line in lines[anchor_index : min(len(lines), anchor_index + lookahead + 1)]:
        if _norm(line).startswith(marker_norm):
            return True
    return False


def _find_header(lines: list[str], anchor_index: int) -> tuple[int, str, str] | None:
    """Return (title line index, title, descriptor) for a valid stat-block anchor."""
    if not _marker_near(lines, anchor_index, "Punti Ferita", 6):
        return None
    if not (
        _marker_near(lines, anchor_index, "Velocità", 8)
        or _marker_near(lines, anchor_index, "Velocita", 8)
    ):
        return None

    first = max(0, anchor_index - 8)
    descriptor_index = next(
        (
            index
            for index in range(anchor_index - 1, first - 1, -1)
            if _line_is_descriptor(lines[index])
        ),
        None,
    )
    if descriptor_index is None:
        return None

    title_index = next(
        (
            index
            for index in range(descriptor_index - 1, max(-1, descriptor_index - 5), -1)
            if lines[index].strip() and _line_is_title_candidate(lines[index])
        ),
        None,
    )
    if title_index is None:
        return None
    title = clean_text(lines[title_index]).strip(" .:;,—–-")
    descriptor = clean_text(lines[descriptor_index])
    return title_index, title, descriptor


def _first_match(patterns: Iterable[str], text: str) -> str:
    for pattern in patterns:
        found = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if found:
            return clean_text(found.group(1)).strip(" .;,")
    return ""


def _attributes(text: str, descriptor: str) -> dict:
    flat = clean_text(text)
    attributes: dict[str, object] = {
        "descrittore_creatura": descriptor,
    }
    patterns = {
        "classe_armatura": (
            r"Classe\s+(?:d['’]\s*)?Armatura\s*[:]?\s*([^\n]{1,80})",
        ),
        "punti_ferita": (
            r"Punti\s+Ferita\s*[:]?\s*([^\n]{1,100})",
        ),
        "velocita": (
            r"Velocit[àa]\s*[:]?\s*([^\n]{1,160})",
        ),
        "tiri_salvezza": (
            r"Tiri\s+Salvezza\s*[:]?\s*([^\n]{1,220})",
        ),
        "abilita": (
            r"Abilit[àa]\s*[:]?\s*([^\n]{1,220})",
        ),
        "vulnerabilita_danni": (
            r"Vulnerabilit[àa]\s+ai\s+Danni\s*[:]?\s*([^\n]{1,220})",
        ),
        "resistenze_danni": (
            r"Resistenze\s+ai\s+Danni\s*[:]?\s*([^\n]{1,220})",
        ),
        "immunita_danni": (
            r"Immunit[àa]\s+ai\s+Danni\s*[:]?\s*([^\n]{1,220})",
        ),
        "immunita_condizioni": (
            r"Immunit[àa]\s+alle\s+Condizioni\s*[:]?\s*([^\n]{1,220})",
        ),
        "sensi": (
            r"Sensi\s*[:]?\s*([^\n]{1,220})",
        ),
        "linguaggi": (
            r"Linguaggi\s*[:]?\s*([^\n]{1,220})",
        ),
        "grado_sfida": (
            r"Grado\s+di\s+Sfida\s*[:]?\s*([^\n]{1,120})",
        ),
    }
    for field, field_patterns in patterns.items():
        value = _first_match(field_patterns, text)
        if value:
            attributes[field] = value

    # Ability scores are frequently rendered as two OCR rows. Keep them only
    # when all six abbreviations and six numeric values are present together.
    ability_match = re.search(
        r"FOR\s+DES\s+COS\s+INT\s+SAG\s+CAR\s+"
        r"([^\n]{3,220})",
        text,
        flags=re.IGNORECASE,
    )
    if ability_match:
        numbers = re.findall(r"\b\d{1,2}\b", ability_match.group(1))
        if len(numbers) >= 6:
            attributes["caratteristiche"] = dict(
                zip(("for", "des", "cos", "int", "sag", "car"), numbers[:6])
            )

    attributes["ha_azioni"] = bool(re.search(r"(?mi)^\s*Azioni\s*$", text))
    attributes["ha_reazioni"] = bool(re.search(r"(?mi)^\s*Reazioni\s*$", text))
    attributes["ha_azioni_leggendarie"] = bool(
        re.search(r"(?mi)^\s*Azioni\s+Leggendarie\s*$", text)
    )
    return attributes


def _core_attributes_are_complete(attributes: dict) -> bool:
    return all(attributes.get(field) for field in ("classe_armatura", "punti_ferita", "velocita"))


def parse_monster_statblocks(
    pages: list[tuple[int, str]],
    source_filename: str,
    source_language: str = "it",
) -> list[dict]:
    """Parse conservative monster candidates from an ordered page window.

    ``pages`` is a list of ``(1-based page number, OCR text)`` pairs.  A record
    can span multiple pages; every touched page is preserved in source_refs.
    """
    flattened: list[tuple[int, str]] = []
    for page_number, text in pages:
        for raw_line in (text or "").splitlines():
            flattened.append((int(page_number), raw_line.strip()))

    raw_lines = [line for _, line in flattened]
    starts: list[tuple[int, int, str, str]] = []
    seen: set[tuple[int, str]] = set()
    for index, line in enumerate(raw_lines):
        if not _core_anchor(line):
            continue
        header = _find_header(raw_lines, index)
        if header is None:
            continue
        title_index, title, descriptor = header
        start_page = flattened[title_index][0]
        normalized = normalize_reference_name(title)
        key = (start_page, normalized)
        if not normalized or key in seen:
            continue
        seen.add(key)
        starts.append((title_index, start_page, title, descriptor))

    starts.sort(key=lambda item: item[0])
    records: list[dict] = []
    for position, (start_index, start_page, title, descriptor) in enumerate(starts):
        next_start = starts[position + 1][0] if position + 1 < len(starts) else len(flattened)
        block_pairs = flattened[start_index:next_start]
        block_lines = [line for _, line in block_pairs if line]
        block_text = "\n".join(block_lines)
        attributes = _attributes(block_text, descriptor)
        if not _core_attributes_are_complete(attributes):
            continue
        normalized_name = normalize_reference_name(title)
        touched_pages = sorted({page for page, line in block_pairs if line})
        source_refs = [
            {
                "filename": source_filename,
                "page": page,
                "logical_page": page,
                "language": source_language,
            }
            for page in touched_pages
        ]
        stable = f"{source_filename}:{start_page}:monster:{normalized_name}"
        flags = ["ocr_da_verificare"]
        if position == len(starts) - 1:
            flags.append("sezione_potenzialmente_continua")
        records.append(
            {
                "id": f"ref_{sha256(stable.encode()).hexdigest()[:24]}",
                "reference_type": "monster",
                "name": title,
                "normalized_name": normalized_name,
                "description": compact_text(block_text),
                "full_text": block_text,
                "attributes": attributes,
                "tags": ["monster"],
                "source_refs": source_refs,
                "review_flags": sorted(flags),
                "start_page": start_page,
                "end_page": max(touched_pages) if touched_pages else start_page,
            }
        )
    return records


def agreed_monster_records(primary: list[dict], comparison: list[dict]) -> list[dict]:
    """Keep only records independently found by both OCR layout modes.

    Name, start page and the three core stat fields must agree after conservative
    normalization.  The returned record keeps the primary transcription but is
    tagged with an explicit independent-agreement flag.
    """
    comparison_by_key = {
        (int(record.get("start_page") or 0), record.get("normalized_name")): record
        for record in comparison
    }
    agreed: list[dict] = []
    for record in primary:
        key = (int(record.get("start_page") or 0), record.get("normalized_name"))
        other = comparison_by_key.get(key)
        if not other:
            continue
        left = record.get("attributes") or {}
        right = other.get("attributes") or {}
        if any(
            _norm(str(left.get(field) or "")) != _norm(str(right.get(field) or ""))
            for field in ("classe_armatura", "punti_ferita", "velocita")
        ):
            continue
        copy = {
            **record,
            "attributes": dict(record.get("attributes") or {}),
            "review_flags": sorted(
                set(record.get("review_flags") or []) | {"ocr_independent_agreement"}
            ),
        }
        copy["attributes"]["ocr_independent_agreement"] = True
        agreed.append(copy)
    return agreed
