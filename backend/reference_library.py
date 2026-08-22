"""Private manual reference catalogue parsing, searching, and card mapping.

Only structured facts derived from supplied manuals are persisted.  PDF bytes
and full page images remain local to the import process and are never exposed
through the API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from copy import deepcopy
import json
import re
import unicodedata
from typing import Callable, Iterable, Optional


REFERENCE_TYPES = (
    "class",
    "subclass",
    "class_feature",
    "spell",
    "feat",
    "race",
    "subrace",
    "monster",
    "ability",
    "weapon",
    "armor",
    "shield",
    "equipment",
    "tool",
    "magic_item",
    "vehicle",
    "ammunition",
    "mount",
    "trade_good",
    "service",
    "other",
)
CHARACTER_CREATION_REFERENCE_TYPES = frozenset({
    "class",
    "subclass",
    "class_feature",
    "spell",
    "feat",
    "race",
    "subrace",
    "weapon",
    "armor",
    "shield",
    "equipment",
    "tool",
    "magic_item",
    "vehicle",
    "ammunition",
    "mount",
    "trade_good",
    "service",
})
UNAVAILABLE_TRANSLATION_STATUSES = frozenset({"failed", "processing"})
CLASS_TITLES = {
    "barbaro", "bardo", "chierico", "druido", "guerriero", "ladro",
    "mago", "monaco", "paladino", "ranger", "stregone", "warlock",
}
SPANISH_CLASS_TITLES = {
    "barbaro", "bardo", "clerigo", "druida", "guerrero", "monje",
    "paladin", "explorador", "picaro", "hechicero", "brujo", "mago",
}
RACE_TITLES = {
    "dragonide", "elfo", "enano", "gnomo", "humano", "mediano",
    "mezzelfo", "mezzorco", "tiefling",
    "draconido", "elfo", "enano", "gnomo", "humano", "mediano",
    "semielfo", "semiorco", "tiefling",
}
CARD_TYPE_BY_REFERENCE_TYPE = {
    "class": "class",
    "subclass": "subclass",
    "class_feature": "feature",
    "spell": "spell",
    "feat": "feat",
    "race": "race",
    "subrace": "race",
    "monster": "monster",
    "ability": "custom",
    "weapon": "weapon",
    "armor": "armor",
    "shield": "armor",
    "equipment": "item",
    "tool": "item",
    "magic_item": "item",
    "vehicle": "item",
    "ammunition": "item",
    "mount": "item",
    "trade_good": "item",
    "service": "item",
    "other": "custom",
}
MAX_CARD_DESCRIPTION = 620


@dataclass
class ReferenceImportReport:
    source_filename: str
    pages_read: int = 0
    pages_needing_ocr: list[int] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)


def normalize_reference_name(value: str) -> str:
    """Return a case/accent/punctuation-insensitive stable title key."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("’", "'").lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def compact_text(value: str, maximum: int = MAX_CARD_DESCRIPTION) -> str:
    value = clean_text(value)
    if len(value) <= maximum:
        return value
    return f"{value[: maximum - 1].rsplit(' ', 1)[0].rstrip(' ,;:')}…"


def reference_content_fingerprint(record: dict) -> str:
    """Identify identical source content without losing a rule's provenance.

    The fingerprint deliberately includes type, normalized title, source
    language, structured attributes, and the original source wording. Matching
    names alone are never enough: a revised rule must remain a separate entry.
    """
    source_text = record.get("source_full_text") or record.get("full_text") or ""
    source_attributes = record.get("source_attributes")
    if source_attributes is None:
        source_attributes = record.get("attributes") or {}
    canonical = {
        "reference_type": record.get("reference_type", ""),
        "normalized_name": record.get("normalized_name") or normalize_reference_name(record.get("name", "")),
        "source_language": record.get("source_language", "it"),
        "full_text": clean_text(source_text),
        "attributes": source_attributes,
    }
    serialized = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


def reference_review_state(record: dict) -> str:
    """Classify a record as safe to automate, pending review, or unavailable.

    Native text without extraction warnings is usable immediately.  OCR/table
    warnings and automated translations are deliberately not: a reviewer must
    explicitly mark those records as verified before they can complete a
    character sheet or answer a manual-content request.
    """
    translation_status = record.get("translation_status", "not_required")
    review_status = record.get("review_status", "pending")
    if translation_status in UNAVAILABLE_TRANSLATION_STATUSES:
        return "review"
    if review_status == "verified":
        return "valid"
    if translation_status == "translated":
        return "review"
    if record.get("review_flags") or review_status == "needs_review":
        return "review"
    return "valid"


def reference_is_trusted(record: dict) -> bool:
    """Whether a record is safe for deterministic character automation."""
    return reference_review_state(record) == "valid"


def source_reference(source_filename: str, source_page: int, source_language: str) -> dict:
    """Keep existing Italian provenance compact while labeling foreign sources."""
    reference = {"filename": source_filename, "page": source_page}
    if source_language != "it":
        reference["language"] = source_language
    return reference


def text_is_usable(value: str) -> bool:
    """Reject broken font mappings while accepting Italian text and tables."""
    value = clean_text(value)
    if len(value) < 80:
        return False
    letters = sum(char.isalpha() for char in value)
    printable = sum(char.isprintable() for char in value)
    return letters / max(len(value), 1) >= 0.32 and printable / max(len(value), 1) >= 0.96


def _title_from_line(value: str) -> Optional[str]:
    value = clean_text(value)
    if not 3 <= len(value) <= 84 or not any(char.isalpha() for char in value):
        return None
    # Some text-native Spanish PDFs use small caps, which PyMuPDF exposes as
    # mixed case (for example "BárBaro"). Recognise only known base class and
    # race titles before applying the conservative heading heuristic below.
    title_key = normalize_reference_name(value)
    if (
        title_key in CLASS_TITLES | SPANISH_CLASS_TITLES | RACE_TITLES
        and value == value.strip(" .:;,")
    ):
        return value.title()
    # Native Italian D&D PDFs use all-caps headings; requiring a high uppercase
    # ratio avoids promoting normal paragraphs or table rows into records.
    letters = [char for char in value if char.isalpha()]
    if sum(char.isupper() for char in letters) / max(len(letters), 1) < 0.78:
        return None
    if value.casefold() in {"indice", "introduzione", "capitolo", "regole base"}:
        return None
    return value.title()


def _record_type(title: str, body: str) -> str:
    sample = f"{title} {body[:900]}".casefold()
    title_key = title.casefold()
    normalized_title = normalize_reference_name(title)
    if normalized_title in CLASS_TITLES | SPANISH_CLASS_TITLES:
        return "class"
    if normalized_title in RACE_TITLES:
        return "race"
    if normalized_title in {"oggetti magici", "oggetto magico", "objetos magicos", "objeto magico"}:
        return "magic_item"
    if normalized_title in {"armature", "armatura", "armature e scudi", "armaduras", "armadura"}:
        return "armor"
    if normalized_title in {"scudi", "scudo", "escudos", "escudo"}:
        return "shield"
    if normalized_title in {
        "armi", "arma", "armi semplici", "armi marziali",
        "armas", "armas simples", "armas marciales",
    }:
        return "weapon"
    if normalized_title in {"strumenti", "strumento", "herramientas", "herramienta"}:
        return "tool"
    if normalized_title in {"veicoli", "veicolo", "vehiculos", "vehiculo"}:
        return "vehicle"
    if normalized_title in {"cavalcature", "animali da tiro", "monturas", "animales de tiro"}:
        return "mount"
    if normalized_title in {"munizioni", "munizione", "municion"}:
        return "ammunition"
    if normalized_title in {"merci commerciali", "beni commerciali", "mercancias"}:
        return "trade_good"
    if normalized_title in {"servizi", "servizio", "servicios", "servicio"}:
        return "service"
    if normalized_title in {"equipaggiamento", "attrezzatura", "equipo"}:
        return "equipment"
    if re.search(r"\b\d+d\d+\b", sample) and any(
        token in sample for token in (
            "taglienti", "perforanti", "contundenti", "proprietà", "proprieta",
            "cortante", "perforante", "contundente", "propiedades",
        )
    ):
        return "weapon"
    if re.search(r"\b(comune|non comune|raro|molto raro|leggendario|artefatto|comun|poco comun|muy raro|legendario|artefacto)\b", sample) and (
        "sintonia" in sample or "sintonía" in sample or "oggetto" in sample or "objeto" in sample
    ):
        return "magic_item"
    if ("classe armatura" in sample and "punti ferita" in sample) or (
        "clase de armadura" in sample and "puntos de golpe" in sample
    ):
        return "monster"
    if "prerequisito" in sample and (
        "talento" in sample or "incremento" in sample or "dote" in sample or "mejora" in sample
    ):
        return "feat"
    if any(token in sample for token in ("tratti razziali", "rasgos raciales", "sottorazza", "subraza")):
        return "subrace" if "sottorazza" in sample or "subraza" in sample else "race"
    if any(token in title_key for token in (
        "archetipo", "arquetipo", "collegio", "colegio", "cammino", "camino",
        "dominio", "circolo", "circulo", "giuramento", "juramento", "tradizione",
        "tradicion", "patto", "pacto", "conclave", "ordine", "via del",
    )):
        return "subclass"
    if ("archetipo" in sample and "quando scegli" in sample) or (
        "arquetipo" in sample and "cuando eliges" in sample
    ):
        return "subclass"
    if (
        any(token in sample for token in ("ottiene", "obtienes")) and "livello" in sample
    ) or (
        "nivel" in sample and any(token in sample for token in ("obtienes", "rasgo", "caracteristica"))
    ):
        return "class_feature"
    if any(token in sample for token in (
        "capacità", "privilegio", "invocazione", "manovra", "capacidad",
        "rasgo", "invocacion", "maniobra",
    )):
        return "ability"
    return "other"


def _attributes(record_type: str, body: str) -> dict:
    flat = clean_text(body)
    attributes: dict = {}
    if record_type == "class":
        hit_die = re.search(r"(?:dado\s+vita|hit\s+die)\s*:?\s*(d\s*\d+)", flat, flags=re.IGNORECASE)
        primary_ability = re.search(
            r"(?:abilità|caratteristica)\s+primaria\s*:?\s*([^.]{2,120})",
            flat,
            flags=re.IGNORECASE,
        )
        saving_throws = re.search(
            r"(?:tiri\s+salvezza|salvezze)\s*:?\s*([^.]{2,160})",
            flat,
            flags=re.IGNORECASE,
        )
        proficiencies = re.search(
            r"(?:competenze|proficiencies)\s*:?\s*([^.]{2,220})",
            flat,
            flags=re.IGNORECASE,
        )
        if hit_die:
            attributes["dado_vita"] = hit_die.group(1).replace(" ", "")
        if primary_ability:
            attributes["abilita_primaria"] = primary_ability.group(1).strip()
        if saving_throws:
            attributes["tiri_salvezza"] = saving_throws.group(1).strip()
        if proficiencies:
            attributes["competenze"] = proficiencies.group(1).strip()
    elif record_type in {"race", "subrace"}:
        patterns = {
            "bonus_caratteristiche": r"(?:incremento|aumento|bonus)[^.]{0,60}(?:caratteristica|abilità)[^.]{0,140}",
            "velocita": r"(?:velocità|velocidad)\s*:?\s*([0-9]+(?:[.,][0-9]+)?\s*(?:metri|m|piedi|feet))",
            "taglia": r"(?:taglia|tamaño)\s*:?\s*([A-Za-zÀ-ÿ]+)",
            "linguaggi": r"(?:linguaggi|idiomas)\s*:?\s*([^.]{2,160})",
        }
        for field, pattern in patterns.items():
            found = re.search(pattern, flat, flags=re.IGNORECASE)
            if found:
                attributes[field] = found.group(1).strip() if found.lastindex else found.group(0).strip()
    elif record_type == "spell":
        spell_text = body or flat
        spell_header = re.search(
            r"(Abjuración|Adivinación|Conjuración|Encantamiento|Evocación|Ilusión|Nigromancia|Transmutación)"
            r"\s+(?:nivel\s+)?(\d+|truco)(?:\s*\((ritual)\))?",
            spell_text,
            flags=re.IGNORECASE,
        )
        if spell_header:
            attributes["scuola"] = spell_header.group(1)
            attributes["livello"] = "Trucchetto" if spell_header.group(2).casefold() == "truco" else spell_header.group(2)
            if spell_header.group(3):
                attributes["rituale"] = "Sì"
        spell_patterns = {
            "tempo_lancio": r"(?mi)^Tiempo de lanzamiento\s*:\s*(.+)$",
            "gittata": r"(?mi)^(?:Alcance|Alance)\s*:\s*(.+)$",
            "componenti": r"(?mi)^Componentes\s*:\s*(.+)$",
            "durata": r"(?mi)^Duración\s*:\s*(.+)$",
        }
        for field, pattern in spell_patterns.items():
            found = re.search(pattern, spell_text, flags=re.IGNORECASE)
            if found:
                attributes[field] = found.group(1).strip()
        if re.search(r"Concentración", spell_text, flags=re.IGNORECASE):
            attributes["concentrazione"] = "Sì"
    elif record_type == "feat":
        match = re.search(r"Prerequisito\s*:\s*([^.]{2,180})", flat, flags=re.IGNORECASE)
        attributes["prerequisito"] = match.group(1).strip() if match else ""
    elif record_type == "monster":
        patterns = {
            "classe_armatura": r"Classe Armatura\s*([0-9]+(?:\s*\([^)]+\))?)",
            "punti_ferita": r"Punti Ferita\s*([0-9]+(?:\s*\([^)]+\))?)",
            "velocita": r"Velocità\s*([^.]{2,140})",
            "grado_sfida": r"Grado di Sfida\s*([0-9/]+)",
        }
        for field, pattern in patterns.items():
            found = re.search(pattern, flat, flags=re.IGNORECASE)
            if found:
                attributes[field] = found.group(1).strip()
    elif record_type in {"class_feature", "ability"}:
        level = re.search(
            r"(?:al|dal|a partir del|en el|a)\s+(\d+)°?\s+(?:livello|nivel)",
            flat,
            flags=re.IGNORECASE,
        )
        if level:
            attributes["livello"] = level.group(1)
    elif record_type in {
        "weapon", "armor", "shield", "equipment", "tool", "magic_item",
        "vehicle", "ammunition", "mount", "trade_good", "service",
    }:
        currency = re.search(
            r"\b([0-9]+(?:[.,][0-9]+)?)\s*(mo|ma|mr|mc|po|pl|pe|pc|m\.?o\.?|m\.?a\.?|m\.?r\.?|m\.?c\.?)\b",
            flat,
            flags=re.IGNORECASE,
        )
        weight = re.search(r"\b([0-9]+(?:[.,][0-9]+)?)\s*(kg|chili|libbre?|libras?)\b", flat, flags=re.IGNORECASE)
        if currency:
            attributes["costo"] = currency.group(0)
        if weight:
            attributes["peso"] = weight.group(0)
        if record_type == "weapon":
            damage = re.search(r"\b([0-9]+d[0-9]+(?:\s*[+\-]\s*[0-9]+)?)\s+([a-zà-ÿ]+)", flat, flags=re.IGNORECASE)
            if damage:
                attributes["danno"] = damage.group(1)
                attributes["tipo_danno"] = damage.group(2)
            properties = re.search(r"(?:proprietà|proprieta|propiedades)\s*:\s*([^.;]{2,180})", flat, flags=re.IGNORECASE)
            if properties:
                attributes["proprieta"] = properties.group(1).strip()
            range_match = re.search(r"(?:gittata|portata|alcance)\s*:\s*([^.;]{2,80})", flat, flags=re.IGNORECASE)
            if range_match:
                attributes["gittata"] = range_match.group(1).strip()
            attributes["categoria"] = "Arma"
        elif record_type in {"armor", "shield"}:
            armor_class = re.search(r"(?:classe armatura|clase de armadura|CA)\s*[:+]?\s*([0-9]+(?:\s*\+\s*[A-Za-z]+)?)", flat, flags=re.IGNORECASE)
            strength = re.search(r"(?:forza minima|requisito di forza|fuerza minima|requisito de fuerza|Fuerza)\s*[:+]?\s*([0-9]+)", flat, flags=re.IGNORECASE)
            if armor_class:
                attributes["classe_armatura"] = armor_class.group(1)
            if strength:
                attributes["forza_minima"] = strength.group(1)
            if re.search(r"(?:svantaggio[^.]{0,80}furtività|desventaja[^.]{0,80}sigilo)", flat, flags=re.IGNORECASE):
                attributes["svantaggio_furtivita"] = "Sì"
            attributes["categoria"] = "Scudo" if record_type == "shield" else "Armatura"
        elif record_type == "magic_item":
            rarity = re.search(r"\b(comune|non comune|raro|molto raro|leggendario|artefatto|comun|poco comun|muy raro|legendario|artefacto)\b", flat, flags=re.IGNORECASE)
            if rarity:
                attributes["rarita"] = rarity.group(1)
            if re.search(r"sintonia|sintonía", flat, flags=re.IGNORECASE):
                attributes["sintonia"] = "Richiede sintonia"
            attributes["categoria"] = "Oggetto magico"
        else:
            attributes["categoria"] = {
                "equipment": "Equipaggiamento",
                "tool": "Strumento",
                "vehicle": "Veicolo",
                "ammunition": "Munizioni",
                "mount": "Cavalcatura",
                "trade_good": "Merce commerciale",
                "service": "Servizio",
            }.get(record_type, "Oggetto")
    return attributes


SPANISH_SPELL_HEADER = re.compile(
    r"^(?:Abjuración|Adivinación|Conjuración|Encantamiento|Evocación|Ilusión|Nigromancia|Transmutación)"
    r"\s+(?:nivel\s+)?(?:\d+|truco)(?:\s*\(ritual\))?\s*$",
    flags=re.IGNORECASE,
)


def _spanish_spell_records(
    text: str,
    source_filename: str,
    source_page: int,
    source_language: str,
) -> list[dict]:
    """Extract native Spanish spell blocks whose title uses mixed small caps."""
    if source_language != "es":
        return []
    lines = [line.strip() for line in (text or "").splitlines()]
    starts = [
        index for index in range(1, len(lines))
        if SPANISH_SPELL_HEADER.match(clean_text(lines[index]))
        and 2 <= len(clean_text(lines[index - 1])) <= 84
        and any(char.isalpha() for char in lines[index - 1])
    ]
    records: list[dict] = []
    for position, header_index in enumerate(starts):
        title = clean_text(lines[header_index - 1]).title()
        # The next spell's title is the line immediately before its school
        # header, so exclude it from the previous spell's source block.
        next_header = starts[position + 1] - 1 if position + 1 < len(starts) else len(lines)
        raw_body = "\n".join(lines[header_index:next_header])
        body = clean_text(raw_body)
        if len(body) < 80:
            continue
        normalized_name = normalize_reference_name(title)
        stable_source = f"{source_filename}:{source_page}:spell:{normalized_name}"
        records.append({
            "id": f"ref_{sha256(stable_source.encode()).hexdigest()[:24]}",
            "reference_type": "spell",
            "name": title,
            "normalized_name": normalized_name,
            "description": compact_text(body),
            "full_text": body,
            "attributes": _attributes("spell", raw_body),
            "tags": ["spell"],
            "source_refs": [source_reference(source_filename, source_page, source_language)],
            "review_flags": ["sezione_potenzialmente_continua"] if position == len(starts) - 1 else [],
        })
    return records


def _equipment_row_records(
    body: str,
    parent_type: str,
    source_filename: str,
    source_page: int,
    source_language: str = "it",
) -> list[dict]:
    """Extract conservative rows from equipment tables.

    OCR and PDF layout engines disagree on column spacing. We only promote a
    row when it contains an unmistakable price/weight/damage/stat token and
    preserve the complete row as its description for later review.
    """
    if parent_type not in {
        "weapon", "armor", "shield", "equipment", "tool", "vehicle",
        "ammunition", "mount", "trade_good", "service",
    }:
        return []
    rows: list[dict] = []
    for raw_line in (body or "").splitlines():
        line = clean_text(raw_line)
        if len(line) < 8 or len(line) > 220:
            continue
        tokens = list(re.finditer(
            r"\b(?:[0-9]+d[0-9]+|[0-9]+(?:[.,][0-9]+)?\s*(?:mo|ma|mr|mc|po|pl|pe|pc|kg|chili|libbre?|libras?))\b",
            line,
            flags=re.IGNORECASE,
        ))
        # A name can contain a weight in parentheses (for example "Ferro
        # (1 kg)"). Prefer a damage roll or a currency column as the first
        # structural field, and only then fall back to a weight token.
        token = next(
            (match for match in tokens if "d" in match.group(0).casefold() or re.search(r"(?:m[oa rc]|p[ol ec])", match.group(0), re.IGNORECASE)),
            tokens[0] if tokens else None,
        )
        if token is None:
            continue
        name = clean_text(line[: token.start()]).strip(" -:;,.")
        if not 2 <= len(name) <= 64 or not re.search(r"[A-Za-zÀ-ÿ]", name):
            continue
        if _title_from_line(name):
            continue
        normalized_name = normalize_reference_name(name)
        if not normalized_name or normalized_name in {
            "nome", "costo", "danno", "peso", "proprieta", "nombre", "coste",
            "danio", "peso", "propiedades",
        }:
            continue
        row_type = (
            "shield"
            if parent_type == "armor"
            and normalize_reference_name(name).startswith(("scudo", "escudo"))
            else parent_type
        )
        stable_source = f"{source_filename}:{source_page}:{row_type}:{normalized_name}"
        rows.append(
            {
                "id": f"ref_{sha256(stable_source.encode()).hexdigest()[:24]}",
                "reference_type": row_type,
                "name": name.title(),
                "normalized_name": normalized_name,
                "description": compact_text(line),
                "full_text": line,
                "attributes": _attributes(row_type, line),
                "tags": [row_type],
                "source_refs": [source_reference(source_filename, source_page, source_language)],
                "review_flags": ["riga_tabella_da_verificare"],
            }
        )
    return rows


def parse_reference_page(
    text: str,
    source_filename: str,
    source_page: int,
    source_language: str = "it",
) -> list[dict]:
    """Extract conservative heading-based records from one text-native page.

    A record is intentionally marked for review when a section can end on a
    following page. This preserves provenance without inventing missing rules.
    """
    lines = [line.strip() for line in (text or "").splitlines()]
    headings = [(index, title) for index, line in enumerate(lines) if (title := _title_from_line(line))]
    spell_records = _spanish_spell_records(text, source_filename, source_page, source_language)
    spell_names = {record["normalized_name"] for record in spell_records}
    records: list[dict] = []
    for heading_index, (line_index, title) in enumerate(headings):
        next_line = headings[heading_index + 1][0] if heading_index + 1 < len(headings) else len(lines)
        body_lines = lines[line_index + 1 : next_line]
        raw_body = "\n".join(body_lines)
        body = clean_text(" ".join(body_lines))
        record_type = _record_type(title, body)
        equipment_rows = _equipment_row_records(
            raw_body, record_type, source_filename, source_page, source_language
        )
        if len(body) < 90:
            records.extend(equipment_rows)
            continue
        normalized_name = normalize_reference_name(title)
        if not normalized_name:
            continue
        if record_type == "other" and normalized_name in spell_names:
            continue
        review_flags = ["sezione_potenzialmente_continua"] if heading_index == len(headings) - 1 else []
        stable_source = f"{source_filename}:{source_page}:{record_type}:{normalized_name}"
        record = {
            "id": f"ref_{sha256(stable_source.encode()).hexdigest()[:24]}",
            "reference_type": record_type,
            "name": title,
            "normalized_name": normalized_name,
            "description": compact_text(body),
            "full_text": body,
            "attributes": _attributes(record_type, body),
            "tags": [],
            "source_refs": [source_reference(source_filename, source_page, source_language)],
            "review_flags": review_flags,
        }
        records.append(record)
        records.extend(equipment_rows)
    return records + spell_records


def extract_reference_records(
    pdf_path: Path,
    ocr_page: Optional[Callable[[object, int], str]] = None,
    start_page: int = 1,
    end_page: Optional[int] = None,
    force_ocr: bool = False,
    source_language: str = "it",
) -> ReferenceImportReport:
    """Read native text, invoking an optional private OCR callback only as needed."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - deployment setup
        raise RuntimeError("PyMuPDF non è installato: aggiungi PyMuPDF alle dipendenze backend.") from exc

    document = fitz.open(pdf_path)
    report = ReferenceImportReport(source_filename=pdf_path.name)
    try:
        first = max(start_page, 1)
        last = min(end_page or len(document), len(document))
        for page_number in range(first, last + 1):
            page = document[page_number - 1]
            text = "" if force_ocr else page.get_text("text")
            extracted_with_ocr = force_ocr
            if not text_is_usable(text):
                if ocr_page is None:
                    report.pages_needing_ocr.append(page_number)
                    continue
                text = ocr_page(page, page_number)
                extracted_with_ocr = True
                if not text_is_usable(text):
                    report.pages_needing_ocr.append(page_number)
                    continue
            report.pages_read += 1
            records = parse_reference_page(text, pdf_path.name, page_number, source_language)
            if extracted_with_ocr:
                for record in records:
                    record["review_flags"] = sorted(
                        set(record.get("review_flags") or []) | {"ocr_da_verificare"}
                    )
            report.records.extend(records)
        return report
    finally:
        document.close()


def merge_reference_records(records: Iterable[dict]) -> list[dict]:
    """Deduplicate identical native content while retaining every source pointer.

    A repeated rule from different manuals is merged only when its original
    wording and extracted facts match exactly. OCR and translated source text
    remains source-scoped until a reviewer can confirm it, avoiding an
    accidental merge of two editions or translations.
    """
    merged: dict[tuple[str, str, str, str], dict] = {}
    source_groups: dict[tuple[str, str, str], tuple[str, str, str, str]] = {}
    content_groups: dict[tuple[str, str, str, str], tuple[str, str, str, str]] = {}
    for candidate in records:
        source_key = candidate.get("source_key", "")
        source_group = (
            candidate["reference_type"],
            candidate["normalized_name"],
            source_key,
        )
        source_language = candidate.get("source_language", "it")
        content_group = (
            candidate["reference_type"],
            candidate["normalized_name"],
            source_language,
            reference_content_fingerprint(candidate),
        )
        # A source-local merge preserves the prior multi-page parsing
        # behavior. Cross-manual merges are intentionally limited to native
        # content: translations and OCR need their own review history.
        can_merge_across_manuals = source_language != "es" and not candidate.get("review_flags")
        key = source_groups.get(source_group)
        if key is None and can_merge_across_manuals:
            key = content_groups.get(content_group)
        if key is None:
            key = content_group if can_merge_across_manuals else (
                candidate["reference_type"],
                candidate["normalized_name"],
                source_language,
                f"{content_group[-1]}:{source_key}",
            )
            merged[key] = {
                **candidate,
                "attributes": dict(candidate.get("attributes") or {}),
                "source_refs": list(candidate.get("source_refs") or []),
                "review_flags": list(candidate.get("review_flags") or []),
                "tags": list(candidate.get("tags") or []),
            }
            if can_merge_across_manuals:
                content_groups[content_group] = key
        source_groups[source_group] = key
        current = merged[key]
        if current is candidate:
            continue
        current["source_refs"].extend(ref for ref in candidate.get("source_refs", []) if ref not in current["source_refs"])
        current["review_flags"] = sorted(set(current["review_flags"]) | set(candidate.get("review_flags") or []))
        current["tags"] = sorted(set(current["tags"]) | set(candidate.get("tags") or []))
        if len(candidate.get("full_text", "")) > len(current.get("full_text", "")):
            current["description"] = candidate["description"]
            current["full_text"] = candidate["full_text"]
            # Keep the source snapshot used for translation in lockstep with
            # the representative record selected for a multi-page section.
            for field_name in (
                "source_name",
                "source_description",
                "source_full_text",
                "source_attributes",
                "source_text_checksum",
            ):
                if field_name in candidate:
                    current[field_name] = candidate[field_name]
        for name, value in (candidate.get("attributes") or {}).items():
            if value and not current["attributes"].get(name):
                current["attributes"][name] = value
    return list(merged.values())


def search_reference_records(
    records: Iterable[dict],
    query: str,
    reference_type: Optional[str] = None,
    limit: int = 15,
) -> list[dict]:
    # Older imports may already contain an identical entry for each manual.
    # Present the canonical merged view even before a later re-import updates
    # those stored records.
    records = merge_reference_records(records)
    needle = normalize_reference_name(query)
    ranked: list[tuple[float, dict]] = []
    for record in records:
        if reference_type and record.get("reference_type") != reference_type:
            continue
        candidate = record.get("normalized_name") or normalize_reference_name(record.get("name", ""))
        haystack = f"{candidate} {normalize_reference_name(' '.join(record.get('tags') or []))}"
        if not needle:
            score = 0.5
        elif candidate == needle:
            score = 1.0
        elif candidate.startswith(needle):
            score = 0.94
        elif needle in haystack:
            score = 0.82
        else:
            score = SequenceMatcher(None, needle, candidate).ratio()
            if score < 0.64:
                continue
        ranked.append((score, record))
    return [record for _, record in sorted(ranked, key=lambda item: (-item[0], item[1]["name"]))[:limit]]


def reference_to_card_payload(record: dict) -> dict:
    reference_type = record.get("reference_type", "other")
    attributes = dict(record.get("attributes") or {})
    card_type = CARD_TYPE_BY_REFERENCE_TYPE.get(reference_type, "custom")
    if card_type == "class":
        attributes = {
            "dado_vita": attributes.get("dado_vita", ""),
            "abilita_primaria": attributes.get("abilita_primaria", ""),
            "tiri_salvezza": attributes.get("tiri_salvezza", ""),
            "competenze": attributes.get("competenze", ""),
            "caratteristiche": attributes.get("caratteristiche", []),
            **attributes,
        }
    elif card_type == "subclass":
        attributes = {
            "dado_vita": attributes.get("dado_vita", ""),
            "abilita_primaria": attributes.get("abilita_primaria", ""),
            "tiri_salvezza": attributes.get("tiri_salvezza", ""),
            "competenze": attributes.get("competenze", ""),
            "caratteristiche": attributes.get("caratteristiche", []),
            **attributes,
        }
    elif card_type == "feature":
        attributes = {
            "livello": attributes.get("livello", ""),
            "benefici": attributes.get("benefici", []),
            **attributes,
        }
    elif card_type == "race":
        attributes = {
            "bonus_caratteristiche": attributes.get("bonus_caratteristiche", ""),
            "velocita": attributes.get("velocita", ""),
            "taglia": attributes.get("taglia", ""),
            "linguaggi": attributes.get("linguaggi", ""),
            "tratti": attributes.get("tratti", []),
            **attributes,
        }
    elif card_type == "feat":
        attributes = {"prerequisito": attributes.get("prerequisito", ""), "benefici": attributes.get("benefici", []), **attributes}
    elif card_type == "spell":
        attributes = {
            "livello": attributes.get("livello", ""),
            "scuola": attributes.get("scuola", ""),
            "tempo_lancio": attributes.get("tempo_lancio", ""),
            "gittata": attributes.get("gittata", ""),
            "componenti": attributes.get("componenti", ""),
            "durata": attributes.get("durata", ""),
            "concentrazione": attributes.get("concentrazione", ""),
            **attributes,
        }
    elif card_type == "monster":
        attributes = {
            "classe_armatura": attributes.get("classe_armatura", ""),
            "punti_ferita": attributes.get("punti_ferita", ""),
            "velocita": attributes.get("velocita", ""),
            "grado_sfida": attributes.get("grado_sfida", ""),
            "azioni": attributes.get("azioni", []),
            **attributes,
        }
    elif card_type == "weapon":
        attributes = {
            "danno": attributes.get("danno", ""),
            "tipo_danno": attributes.get("tipo_danno", ""),
            "proprieta": attributes.get("proprieta", ""),
            "gittata": attributes.get("gittata", ""),
            "peso": attributes.get("peso", ""),
            "costo": attributes.get("costo", ""),
            "categoria": attributes.get("categoria", "Arma"),
            **attributes,
        }
    elif card_type == "armor":
        attributes = {
            "classe_armatura": attributes.get("classe_armatura", ""),
            "forza_minima": attributes.get("forza_minima", ""),
            "svantaggio_furtivita": attributes.get("svantaggio_furtivita", ""),
            "peso": attributes.get("peso", ""),
            "costo": attributes.get("costo", ""),
            "categoria": attributes.get("categoria", "Armatura"),
            **attributes,
        }
    elif card_type == "item":
        attributes = {
            "categoria": attributes.get("categoria", "Oggetto"),
            "costo": attributes.get("costo", ""),
            "peso": attributes.get("peso", ""),
            "proprieta": attributes.get("proprieta", ""),
            "rarita": attributes.get("rarita", ""),
            "sintonia": attributes.get("sintonia", ""),
            **attributes,
        }
    return {
        "reference_id": record.get("id"),
        "reference_ids": [record["id"]] if record.get("id") else [],
        "name": record.get("name", ""),
        "description": compact_text(record.get("description") or record.get("full_text", "")),
        "story": f"Dati regolamentari dalla biblioteca privata · {record.get('reference_type', 'contenuto')}.",
        "attributes": attributes,
        "card_type": card_type,
        "source": "biblioteca_privata",
        "reference_type": reference_type,
        "source_language": record.get("source_language", "it"),
        "content_language": (
            "it"
            if record.get("translation_status") == "translated"
            else record.get("source_language", "it")
        ),
        "source_refs": record.get("source_refs", []),
    }


def reference_content_checksum(record: dict) -> str:
    """Return a stable rendered-content revision for a private reference record.

    The import checksum identifies source text, but a card also depends on
    translated fields, structured attributes, provenance, and review state.
    Include each rendered input so a correction to any of them is visible to
    linked cards.  The source checksum remains part of the revision where it
    exists, while the snapshot stores it separately for provenance.
    """
    stable_content = {
        "source_text_checksum": record.get("source_text_checksum", ""),
        "name": record.get("name", ""),
        "description": record.get("description", ""),
        "full_text": record.get("full_text", ""),
        "attributes": record.get("attributes", {}),
        "source_refs": record.get("source_refs", []),
        "translation_status": record.get("translation_status", "not_required"),
        "review_status": record.get("review_status", "pending"),
        "review_flags": record.get("review_flags", []),
    }
    return sha256(
        json.dumps(stable_content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def reference_snapshot(record: dict, saved_at: str = "") -> dict:
    """Create the compact, private source snapshot kept with a derived card."""
    payload = reference_to_card_payload(record)
    return {
        "reference_id": record.get("id", ""),
        "reference_type": record.get("reference_type", "other"),
        "name": record.get("name", ""),
        "description": record.get("description", ""),
        "full_text": record.get("full_text", ""),
        "attributes": deepcopy(record.get("attributes") or {}),
        "source_refs": deepcopy(record.get("source_refs") or []),
        "source_language": record.get("source_language", "it"),
        "translation_status": record.get("translation_status", "not_required"),
        "source_text_checksum": record.get("source_text_checksum", ""),
        "content_revision": reference_content_checksum(record),
        "reference_updated_at": record.get("updated_at", ""),
        "saved_at": saved_at,
        "derived_attributes": deepcopy(payload.get("attributes") or {}),
        "derived_card_fields": {
            "name": payload.get("name", ""),
            "description": payload.get("description", ""),
            "story": payload.get("story", ""),
            "language": payload.get("content_language", "it"),
        },
    }


def reference_snapshot_changed(snapshot: dict, record: dict) -> bool:
    """Whether a record now differs from the version acknowledged by a card."""
    if snapshot.get("content_revision"):
        return snapshot["content_revision"] != reference_content_checksum(record)
    # Legacy snapshots already contain the rendered data needed to make an
    # equivalent revision. Compare those fields directly, not merely the old
    # import checksum: translations, attributes, and page provenance can all
    # change while the source text remains the same.
    current = reference_snapshot(record)
    rendered_fields = (
        "name", "description", "full_text", "attributes", "source_refs",
        "source_language", "translation_status",
    )
    if any(snapshot.get(field) != current.get(field) for field in rendered_fields):
        return True
    return snapshot.get("source_text_checksum") != current.get("source_text_checksum")


def reference_snapshot_change_fields(snapshot: dict, record: dict) -> list[str]:
    """Summarise changed source sections for comparison UIs."""
    current = reference_snapshot(record)
    labels = []
    if snapshot.get("name") != current["name"]:
        labels.append("titolo")
    if snapshot.get("description") != current["description"] or snapshot.get("full_text") != current["full_text"]:
        labels.append("testo")
    if snapshot.get("attributes") != current["attributes"]:
        labels.append("attributi")
    if snapshot.get("source_refs") != current["source_refs"]:
        labels.append("riferimenti di pagina")
    return labels or ["contenuto"]