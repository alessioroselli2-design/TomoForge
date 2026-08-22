"""Private D&D spell catalogue parsing and card mapping helpers.

The source PDFs are deliberately read only by the import command/API.  Their
binary files and raw page text are never served by the application.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import re
import unicodedata
from typing import Iterable


CLASS_NAMES = ("Bardo", "Chierico", "Druido", "Mago", "Paladino", "Ranger", "Stregone", "Warlock")
FIELD_HEADERS = ("CASTING TIME", "RANGE", "COMPONENTS", "DURATION")
MAX_CARD_DESCRIPTION = 620


def normalize_spell_name(value: str) -> str:
    """Return a case/accent/punctuation-insensitive stable spell key."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("’", "'").lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def compact_text(value: str, maximum: int = MAX_CARD_DESCRIPTION) -> str:
    text = clean_text(value)
    if len(text) <= maximum:
        return text
    shortened = text[: maximum - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{shortened}…"


def _source_class(pdf_path: Path) -> str:
    filename = normalize_spell_name(pdf_path.stem)
    for class_name in CLASS_NAMES:
        if normalize_spell_name(class_name) in filename:
            return class_name
    return pdf_path.stem


def _field_value(segment: str, header: str, next_header: str) -> str:
    match = re.search(
        rf"{re.escape(header)}\s*\n(?P<value>.*?)(?=\n{re.escape(next_header)}\s*\n)",
        segment,
        flags=re.DOTALL,
    )
    value = clean_text(match.group("value")) if match else ""
    return re.sub(r"^(?:Gittata|Componenti|Durata|Tempo di lancio)\s*:\s*", "", value, flags=re.IGNORECASE)


def _parse_level_and_school(value: str) -> tuple[str, str]:
    value = clean_text(value)
    if value.lower().startswith("trucchetto"):
        return "Trucchetto", value[len("trucchetto"):].strip()
    match = re.match(r"(?P<level>\d+)°?\s+livello\s*(?P<school>.*)", value, flags=re.IGNORECASE)
    if not match:
        return "", value
    return match.group("level"), match.group("school").strip()


def _title_and_body(after_duration: str) -> tuple[str, str, str]:
    """Separate duration, title and body from a card segment.

    The PDFs place the name in an uppercase line immediately after duration.
    This intentionally leaves imperfect blocks reviewable instead of guessing.
    """
    lines = [line.strip() for line in after_duration.splitlines()]
    title_index = next(
        (
            index
            for index, line in enumerate(lines)
            if re.fullmatch(r"[A-ZÀ-Ý0-9'’(),.\- ]{3,}", line or "")
            and any(character.isalpha() for character in line)
        ),
        None,
    )
    if title_index is None:
        return clean_text(after_duration), "", ""
    return clean_text("\n".join(lines[:title_index])), lines[title_index].title(), "\n".join(lines[title_index + 1 :]).strip()


def _extract_metadata(body: str, default_class: str) -> tuple[str, str, str, list[str], list[str]]:
    """Return description, level, school, classes, review flags."""
    flags: list[str] = []
    class_pattern = "|".join(re.escape(class_name) for class_name in CLASS_NAMES)
    matches = list(
        re.finditer(
            rf"(?:^|\n)(?P<class>{class_pattern})(?:\s+\((?P<source>[^)]+)\))?\s*\n"
            rf"(?P<level>(?:trucchetto|\d+°?\s+livello)\b[^\n]*)\s*$",
            body,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    if not matches:
        flags.append("metadati_finali_non_rilevati")
        return clean_text(body), "", "", [default_class], flags

    metadata = matches[-1]
    description = clean_text(body[: metadata.start()])
    level, school = _parse_level_and_school(metadata.group("level"))
    classes = [metadata.group("class").title()]
    if not description:
        flags.append("descrizione_vuota")
    if not level:
        flags.append("livello_non_rilevato")
    if not school:
        flags.append("scuola_non_rilevata")
    return description, level, school, classes, flags


def parse_spell_page(text: str, source_filename: str, source_page: int, source_class: str) -> list[dict]:
    """Parse all complete-looking spell cards from one text-native PDF page."""
    # The Ranger source uses the same schema with Italian field headers.
    text = re.sub(r"(?m)^TEMPO DI LANCIO\s*$", "CASTING TIME", text or "")
    text = re.sub(r"(?m)^GITTATA\s*$", "RANGE", text)
    text = re.sub(r"(?m)^COMPONENTI\s*$", "COMPONENTS", text)
    text = re.sub(r"(?m)^DURATA\s*$", "DURATION", text)
    blocks = re.split(r"(?=CASTING TIME\s*\n)", text or "")
    records: list[dict] = []
    for block in blocks:
        if not block.startswith("CASTING TIME"):
            continue
        casting_time = _field_value(block, "CASTING TIME", "RANGE")
        spell_range = _field_value(block, "RANGE", "COMPONENTS")
        components = _field_value(block, "COMPONENTS", "DURATION")
        duration_section = block.split("DURATION", 1)
        if len(duration_section) != 2 or not casting_time:
            continue
        duration, name, body = _title_and_body(duration_section[1].lstrip(" \n"))
        if not name:
            continue
        description, level, school, classes, flags = _extract_metadata(body, source_class)
        records.append(
            {
                "name": name,
                "normalized_name": normalize_spell_name(name),
                "level": level,
                "school": school,
                "casting_time": casting_time,
                "range": spell_range,
                "components": components,
                "duration": duration,
                "description": description,
                "classes": classes,
                "source_refs": [{"filename": source_filename, "page": source_page}],
                "review_flags": flags,
            }
        )
    return records


def extract_spell_records(pdf_path: Path) -> list[dict]:
    """Extract structured spell records from one supplied, text-native PDF."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - exercised in deployment setup
        raise RuntimeError("PyMuPDF non è installato: aggiungi PyMuPDF alle dipendenze backend.") from exc

    source_class = _source_class(pdf_path)
    document = fitz.open(pdf_path)
    try:
        records = []
        for page_index, page in enumerate(document):
            records.extend(parse_spell_page(page.get_text("text"), pdf_path.name, page_index + 1, source_class))
        return records
    finally:
        document.close()


def merge_spell_records(records: Iterable[dict]) -> list[dict]:
    """Deduplicate a catalogue, retaining all class/source references."""
    merged: dict[str, dict] = {}
    for record in records:
        key = record["normalized_name"]
        if key not in merged:
            merged[key] = {**record, "classes": list(record["classes"]), "source_refs": list(record["source_refs"])}
            continue
        current = merged[key]
        current["classes"] = sorted(set(current["classes"]) | set(record["classes"]))
        current["source_refs"].extend(
            ref for ref in record["source_refs"] if ref not in current["source_refs"]
        )
        current["review_flags"] = sorted(set(current["review_flags"]) | set(record["review_flags"]))
        for field in ("level", "school", "casting_time", "range", "components", "duration", "description"):
            if not current.get(field) and record.get(field):
                current[field] = record[field]
    return list(merged.values())


def search_spell_records(records: Iterable[dict], query: str, limit: int = 12) -> list[dict]:
    """Rank private spell records by normalized exact, prefix and fuzzy matches."""
    needle = normalize_spell_name(query)
    if not needle:
        return list(records)[:limit]

    ranked: list[tuple[float, dict]] = []
    for record in records:
        candidate = record.get("normalized_name") or normalize_spell_name(record.get("name", ""))
        if candidate == needle:
            score = 1.0
        elif candidate.startswith(needle):
            score = 0.94
        elif needle in candidate:
            score = 0.82
        else:
            score = SequenceMatcher(None, needle, candidate).ratio()
            if score < 0.64:
                continue
        ranked.append((score, record))
    return [record for _, record in sorted(ranked, key=lambda item: (-item[0], item[1]["name"]))[:limit]]


def spell_to_card_payload(spell: dict) -> dict:
    """Map a source spell to the card fields without changing canonical facts."""
    duration = spell.get("duration", "")
    return {
        "reference_id": spell.get("id"),
        "reference_ids": [spell["id"]] if spell.get("id") else [],
        "rule_source": {
            "source_kind": "spell",
            "source_id": spell.get("id", ""),
            "name": spell.get("name", ""),
            "reference_type": "spell",
            "source_refs": spell.get("source_refs", []),
        },
        "name": spell.get("name", ""),
        "description": compact_text(spell.get("description", "")),
        "story": f"Dati regolamentari dal Grimorio privato · {', '.join(spell.get('classes', []))}.",
        "attributes": {
            "livello": spell.get("level", ""),
            "scuola": spell.get("school", ""),
            "azione": spell.get("casting_time", ""),
            "tempo_lancio": spell.get("casting_time", ""),
            "gittata": spell.get("range", ""),
            "area": "",
            "componenti": spell.get("components", ""),
            "durata": duration,
            "concentrazione": "Sì" if "concentrazione" in duration.casefold() else "No",
            "danno": "",
            "effetto": "",
        },
        "source": "grimorio",
        "source_refs": spell.get("source_refs", []),
        "source_language": spell.get("source_language", "it"),
        "content_language": spell.get("content_language", spell.get("source_language", "it")),
    }