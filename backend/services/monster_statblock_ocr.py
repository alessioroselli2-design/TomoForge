"""Conservative parser for D&D 5e monster stat blocks extracted by OCR.

This parser is intentionally separate from the generic heading/table parser.
Monster pages have dense two-column stat blocks whose attack rows look like
weapons to a generic document parser. A candidate is accepted only when a
size/type descriptor is immediately followed by the core armor/HP/speed
stat-block markers. Callers should still require independent OCR agreement
before persisting any candidate.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from hashlib import sha256
from typing import Iterable

from reference_library import clean_text, compact_text, normalize_reference_name
from services.monster_guided_matcher import guided_core_merge
from services.monster_name_diagnostics import (
    compact_name_boundary_match,
    compact_name_bounded_edit_match,
    compact_name_containment_match,
)
from services.monster_semantic_diagnostics import deterministic_core_field_matches

_SIZE_WORDS = (
    "minuscolo",
    "piccolo",
    "medio",
    "grande",
    "enorme",
    "mastodontico",
    "tiny",
    "small",
    "medium",
    "large",
    "huge",
    "gargantuan",
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
    "aberration",
    "beast",
    "celestial",
    "construct",
    "dragon",
    "elemental",
    "fey",
    "fiend",
    "giant",
    "monstrosity",
    "ooze",
    "plant",
    "undead",
    "humanoid",
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
    "armor class",
    "hit points",
    "speed",
    "str ",
    "dex ",
    "con ",
    "wis ",
    "cha ",
    "saving throws",
    "skills",
    "damage vulnerabilities",
    "damage resistances",
    "damage immunities",
    "condition immunities",
    "senses",
    "languages",
    "challenge",
    "proficiency bonus",
    "actions",
    "bonus actions",
    "reactions",
    "legendary actions",
    "lair actions",
)


def _norm(value: str) -> str:
    return normalize_reference_name(clean_text(value or ""))


def _normalize_monster_name(value: str) -> str:
    """Normalize only unambiguous OCR separators in a monster heading."""
    value = "".join(char for char in value or "" if unicodedata.category(char) != "Cf")
    value = re.sub(r"(?<=\w)[|¦](?=\w)", "", value)

    # OCR sometimes emits letter-spaced all-caps headings. Rejoin only runs of
    # at least three standalone uppercase letters; ordinary multiword headings
    # and two-letter initials retain their word boundaries.
    letter_spaced_heading = re.compile(r"(?:[A-ZÀ-ÖØ-Þ]\s+){2,}[A-ZÀ-ÖØ-Þ]")
    if letter_spaced_heading.fullmatch(value.strip()):
        value = re.sub(r"\s+", "", value)
    return normalize_reference_name(value)


def _line_is_descriptor(line: str) -> bool:
    value = _norm(line)
    return (
        any(re.search(rf"\b{re.escape(size)}\b", value) for size in _SIZE_WORDS)
        and any(
            re.search(rf"\b{re.escape(creature_type)}\b", value)
            for creature_type in _CREATURE_TYPE_WORDS
        )
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
    # A monster title is normally a short heading. Avoid narrative lines that
    # happen to precede a descriptor because OCR column order can interleave text.
    words = normalized.split()
    if len(words) > 8:
        return False
    letters = [ch for ch in raw if ch.isalpha()]
    upper_ratio = sum(ch.isupper() for ch in letters) / max(len(letters), 1)
    titleish_ratio = sum(word[:1].isupper() for word in raw.split() if word) / max(
        len(raw.split()), 1
    )
    return upper_ratio >= 0.62 or titleish_ratio >= 0.7


def _core_anchor(line: str) -> bool:
    value = _norm(line)
    return (
        value.startswith("classe armatura")
        or value.startswith("classe d armatura")
        or value.startswith("armor class")
    )


def _marker_near(
    lines: list[str], anchor_index: int, marker: str, lookahead: int = 8
) -> bool:
    marker_norm = _norm(marker)
    for line in lines[anchor_index : min(len(lines), anchor_index + lookahead + 1)]:
        if _norm(line).startswith(marker_norm):
            return True
    return False


def _has_any_marker_near(
    lines: list[str],
    anchor_index: int,
    markers: tuple[str, ...],
    lookahead: int,
) -> bool:
    return any(
        _marker_near(lines, anchor_index, marker, lookahead) for marker in markers
    )


def _find_header(lines: list[str], anchor_index: int) -> tuple[int, str, str] | None:
    """Return (title line index, title, descriptor) for a valid stat-block anchor."""
    if not _has_any_marker_near(
        lines,
        anchor_index,
        ("Punti Ferita", "Hit Points"),
        6,
    ):
        return None
    if not _has_any_marker_near(
        lines,
        anchor_index,
        ("Velocità", "Velocita", "Speed"),
        8,
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
    """Map Italian and English source labels into one canonical Italian schema."""
    attributes: dict[str, object] = {
        "descrittore_creatura": descriptor,
    }
    patterns = {
        "classe_armatura": (
            r"Classe\s+(?:d['’]\s*)?Armatura\s*[:]?\s*([^\n]{1,80})",
            r"Armor\s+Class\s*[:]?\s*([^\n]{1,80})",
        ),
        "punti_ferita": (
            r"Punti\s+Ferita\s*[:]?\s*([^\n]{1,100})",
            r"Hit\s+Points\s*[:]?\s*([^\n]{1,100})",
        ),
        "velocita": (
            r"Velocit[àa]\s*[:]?\s*([^\n]{1,160})",
            r"Speed\s*[:]?\s*([^\n]{1,160})",
        ),
        "tiri_salvezza": (
            r"Tiri\s+Salvezza\s*[:]?\s*([^\n]{1,220})",
            r"Saving\s+Throws\s*[:]?\s*([^\n]{1,220})",
        ),
        "abilita": (
            r"Abilit[àa]\s*[:]?\s*([^\n]{1,220})",
            r"Skills\s*[:]?\s*([^\n]{1,220})",
        ),
        "vulnerabilita_danni": (
            r"Vulnerabilit[àa]\s+ai\s+Danni\s*[:]?\s*([^\n]{1,220})",
            r"Damage\s+Vulnerabilities\s*[:]?\s*([^\n]{1,220})",
        ),
        "resistenze_danni": (
            r"Resistenze\s+ai\s+Danni\s*[:]?\s*([^\n]{1,220})",
            r"Damage\s+Resistances\s*[:]?\s*([^\n]{1,220})",
        ),
        "immunita_danni": (
            r"Immunit[àa]\s+ai\s+Danni\s*[:]?\s*([^\n]{1,220})",
            r"Damage\s+Immunities\s*[:]?\s*([^\n]{1,220})",
        ),
        "immunita_condizioni": (
            r"Immunit[àa]\s+alle\s+Condizioni\s*[:]?\s*([^\n]{1,220})",
            r"Condition\s+Immunities\s*[:]?\s*([^\n]{1,220})",
        ),
        "sensi": (
            r"Sensi\s*[:]?\s*([^\n]{1,220})",
            r"Senses\s*[:]?\s*([^\n]{1,220})",
        ),
        "linguaggi": (
            r"Linguaggi\s*[:]?\s*([^\n]{1,220})",
            r"Languages\s*[:]?\s*([^\n]{1,220})",
        ),
        "grado_sfida": (
            r"Grado\s+di\s+Sfida\s*[:]?\s*([^\n]{1,120})",
            r"Challenge\s*[:]?\s*([^\n]{1,120})",
        ),
    }
    for field, field_patterns in patterns.items():
        value = _first_match(field_patterns, text)
        if value:
            attributes[field] = value

    # Ability scores are frequently rendered as two OCR rows. Keep them only
    # when all six abbreviations and six numeric values are present together.
    ability_headers = (
        (
            r"FOR\s+DES\s+COS\s+INT\s+SAG\s+CAR\s+([^\n]{3,220})",
            ("for", "des", "cos", "int", "sag", "car"),
        ),
        (
            r"STR\s+DEX\s+CON\s+INT\s+WIS\s+CHA\s+([^\n]{3,220})",
            ("for", "des", "cos", "int", "sag", "car"),
        ),
    )
    for pattern, canonical_fields in ability_headers:
        ability_match = re.search(pattern, text, flags=re.IGNORECASE)
        if not ability_match:
            continue
        numbers = re.findall(r"\b\d{1,2}\b", ability_match.group(1))
        if len(numbers) >= 6:
            attributes["caratteristiche"] = dict(zip(canonical_fields, numbers[:6]))
            break

    attributes["ha_azioni"] = bool(re.search(r"(?mi)^\s*(?:Azioni|Actions)\s*$", text))
    attributes["ha_reazioni"] = bool(
        re.search(r"(?mi)^\s*(?:Reazioni|Reactions)\s*$", text)
    )
    attributes["ha_azioni_leggendarie"] = bool(
        re.search(r"(?mi)^\s*(?:Azioni\s+Leggendarie|Legendary\s+Actions)\s*$", text)
    )
    return attributes


def _core_attributes_are_complete(attributes: dict) -> bool:
    return all(
        attributes.get(field)
        for field in ("classe_armatura", "punti_ferita", "velocita")
    )


def parse_monster_statblocks(
    pages: list[tuple[int, str]],
    source_filename: str,
    source_language: str = "it",
) -> list[dict]:
    """Parse conservative monster candidates from an ordered page window.

    ``pages`` is a list of ``(1-based page number, OCR text)`` pairs. A record
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
        normalized = _normalize_monster_name(title)
        key = (start_page, normalized)
        if not normalized or key in seen:
            continue
        seen.add(key)
        starts.append((title_index, start_page, title, descriptor))

    starts.sort(key=lambda item: item[0])
    records: list[dict] = []
    for position, (start_index, start_page, title, descriptor) in enumerate(starts):
        next_start = (
            starts[position + 1][0] if position + 1 < len(starts) else len(flattened)
        )
        block_pairs = flattened[start_index:next_start]
        block_lines = [line for _, line in block_pairs if line]
        block_text = "\n".join(block_lines)
        attributes = _attributes(block_text, descriptor)
        if not _core_attributes_are_complete(attributes):
            continue
        normalized_name = _normalize_monster_name(title)
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
    """Keep records independently supported by both OCR layout modes.

    Exact same-page/name matches keep the existing conservative path. If there is
    no exact-name candidate, the guided path may consider one unique same-page
    strict containment or bounded OCR-edit candidate. A unique multi-token
    identity may also align across one adjacent page. Fuzzy and adjacent matches
    require all three core fields to agree deterministically; an otherwise
    ambiguous same-page fuzzy set is accepted only when exactly one pair has
    that complete independent core agreement. Containment keeps the existing
    guided residual gates. All matches retain review and provenance.
    """
    comparison_by_key: dict[tuple[int, str], list[dict]] = defaultdict(list)
    comparison_by_page: dict[int, list[dict]] = defaultdict(list)
    for other in comparison:
        start_page = int(other.get("start_page") or 0)
        normalized_name = str(other.get("normalized_name") or "")
        comparison_by_key[(start_page, normalized_name)].append(other)
        comparison_by_page[start_page].append(other)

    agreed: list[dict] = []
    for record in primary:
        start_page = int(record.get("start_page") or 0)
        normalized_name = str(record.get("normalized_name") or "")
        exact_matches = comparison_by_key.get((start_page, normalized_name), [])
        guided_name_containment = False
        clean_identity_only = False

        if len(exact_matches) == 1:
            other = exact_matches[0]
        elif len(exact_matches) == 0:
            containment_matches = [
                other
                for other in comparison_by_page.get(start_page, [])
                if compact_name_containment_match(
                    normalized_name,
                    str(other.get("normalized_name") or ""),
                )
            ]
            if len(containment_matches) == 1:
                other = containment_matches[0]
                guided_name_containment = True
            elif len(containment_matches) > 1:
                continue
            else:
                fuzzy_matches = [
                    other
                    for other in comparison_by_page.get(start_page, [])
                    if compact_name_bounded_edit_match(
                        normalized_name,
                        str(other.get("normalized_name") or ""),
                    )
                    or compact_name_boundary_match(
                        normalized_name,
                        str(other.get("normalized_name") or ""),
                    )
                ]
                if len(fuzzy_matches) == 1:
                    other = fuzzy_matches[0]
                    clean_identity_only = True
                elif len(fuzzy_matches) > 1:
                    left_attributes = record.get("attributes") or {}
                    clean_fuzzy_matches = []
                    for fuzzy_match in fuzzy_matches:
                        deterministic = deterministic_core_field_matches(
                            left_attributes,
                            fuzzy_match.get("attributes") or {},
                        )
                        if all(
                            deterministic.get(f"{field}_deterministic_match", False)
                            for field in (
                                "classe_armatura",
                                "punti_ferita",
                                "velocita",
                            )
                        ):
                            clean_fuzzy_matches.append(fuzzy_match)
                    if len(clean_fuzzy_matches) != 1:
                        continue
                    other = clean_fuzzy_matches[0]
                    clean_identity_only = True
                else:
                    adjacent_matches = [
                        other
                        for page in (start_page - 1, start_page + 1)
                        for other in comparison_by_page.get(page, [])
                        if len(normalized_name.split()) >= 2
                        and len(str(other.get("normalized_name") or "").split()) >= 2
                        and (
                            normalized_name == str(other.get("normalized_name") or "")
                            or compact_name_containment_match(
                                normalized_name,
                                str(other.get("normalized_name") or ""),
                            )
                            or compact_name_bounded_edit_match(
                                normalized_name,
                                str(other.get("normalized_name") or ""),
                            )
                            or compact_name_boundary_match(
                                normalized_name,
                                str(other.get("normalized_name") or ""),
                            )
                        )
                    ]
                    if len(adjacent_matches) != 1:
                        continue
                    other = adjacent_matches[0]
                    clean_identity_only = True
        else:
            continue

        left = record.get("attributes") or {}
        right = other.get("attributes") or {}
        exact_core_match = not any(
            _norm(str(left.get(field) or "")) != _norm(str(right.get(field) or ""))
            for field in ("classe_armatura", "punti_ferita", "velocita")
        )

        deterministic = deterministic_core_field_matches(left, right)
        all_deterministic = all(
            deterministic.get(f"{field}_deterministic_match", False)
            for field in ("classe_armatura", "punti_ferita", "velocita")
        )

        if clean_identity_only:
            if not all_deterministic:
                continue
            guided_values = guided_core_merge(
                left,
                right,
                allow_clean_deterministic_match=True,
            )
            if guided_values is None:
                continue
        elif guided_name_containment:
            left_name_tokens = normalized_name.split()
            right_name_tokens = str(other.get("normalized_name") or "").split()
            multi_token_containment = bool(
                len(left_name_tokens) >= 2 and len(right_name_tokens) >= 2
            )
            guided_values = guided_core_merge(
                left,
                right,
                allow_clean_deterministic_match=multi_token_containment,
            )
            if guided_values is None:
                continue
        else:
            # A unique exact normalized-name match on the same source page is
            # already independently identity-bound. Permit the guided matcher
            # to accept presentation-only differences when every core field is
            # both semantically and deterministically identical. This does not
            # relax page, name, uniqueness, or numeric agreement.
            guided_values = (
                None
                if exact_core_match
                else guided_core_merge(
                    left,
                    right,
                    allow_clean_deterministic_match=True,
                )
            )
            if not exact_core_match and guided_values is None:
                continue

        review_flags = set(record.get("review_flags") or []) | {
            "ocr_independent_agreement"
        }
        attributes = dict(record.get("attributes") or {})
        if guided_values is not None:
            attributes.update(guided_values)
            attributes["ocr_guided_core_merge"] = True
            review_flags.add("ocr_guided_core_merge")

        copy = {
            **record,
            "attributes": attributes,
            "review_flags": sorted(review_flags),
        }
        copy["attributes"]["ocr_independent_agreement"] = True
        if exact_core_match or all_deterministic:
            copy["attributes"]["ocr_clean_deterministic_core_agreement"] = True
        agreed.append(copy)
    return agreed
