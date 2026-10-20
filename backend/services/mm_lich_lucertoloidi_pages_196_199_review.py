"""Read-only core-stat audit of four original Italian MM blocks on pp196–199.

The owner-provided scanned PDF was visually inspected page by page, and its
353-page SHA-256 was checked against the live Supabase authority. Page 197
contains Lich lore/lair rules only; it is NOT an additional statblock.
Re/Regina Lucertola is ONE shared statblock, not two monsters.
No private scans or full action text are stored in this source file.
"""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import (
    monster_identity_sanity_flags,
    monster_semantic_numeric_flags,
)

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES = 353
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")
_SOURCE: dict[str, dict[str, Any]] = {
    "Lich": {
        "page": 196, "type": "Non morto", "size": "Medio", "subtype": "",
        "align": "qualsiasi allineamento malvagio",
        "ac": "17 (armatura naturale)", "hp": "135 (18d8 + 54)",
        "speed": "9 m", "gs": "21", "scores": [11, 16, 16, 20, 14, 16],
        "actions": ["Tocco Paralizzante"],
        "legendary": ["Trucchetto", "Tocco Paralizzante", "Sguardo Terrificante", "Distruggere Vita"],
        "traits": ["Resistenza Leggendaria (3/Giorno)", "Ringiovanimento",
                   "Incantesimi", "Resistenza allo Scacciare"],
    },
    "Lucertoloide": {
        "page": 198, "type": "Umanoide", "size": "Medio", "subtype": "lucertoloide",
        "align": "neutrale", "ac": "15 (armatura naturale, scudo)",
        "hp": "22 (4d8 + 4)", "speed": "9 m, nuotare 9 m",
        "gs": "1/2", "scores": [15, 10, 13, 7, 12, 7],
        "actions": ["Multiattacco", "Morso", "Randello Pesante", "Giavellotto",
                    "Scudo Chiodato"],
        "legendary": [], "traits": ["Trattenere il Respiro"],
    },
    "Lucertoloide Sciamano": {
        "page": 199, "type": "Umanoide", "size": "Medio", "subtype": "lucertoloide",
        "align": "neutrale", "ac": "13 (armatura naturale)",
        "hp": "27 (5d8 + 5)", "speed": "9 m, nuotare 9 m",
        "gs": "2", "scores": [15, 10, 13, 10, 15, 8],
        "actions": ["Multiattacco (Solo Forma di Lucertoloide)", "Morso",
                    "Artigli", "Cambiare Forma (Ricarica dopo un Riposo Breve o Lungo)"],
        "legendary": [],
        "traits": ["Trattenere il Respiro", "Incantesimi (Solo Forma di Lucertoloide)"],
    },
    "Re/Regina Lucertola": {
        "page": 199, "type": "Umanoide", "size": "Medio", "subtype": "lucertoloide",
        "align": "caotico malvagio", "ac": "15 (armatura naturale)",
        "hp": "78 (12d8 + 24)", "speed": "9 m, nuotare 9 m",
        "gs": "4", "scores": [17, 12, 15, 11, 11, 15],
        "actions": ["Multiattacco", "Morso", "Artigli", "Tridente"],
        "legendary": [], "traits": ["Trattenere il Respiro", "Trafiggere"],
    },
}
SEALED = {
    name: (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["actions"]), tuple(d["legendary"]), tuple(d["traits"]),
    )
    for name, d in _SOURCE.items()
}
MONSTERS = deepcopy(_SOURCE)


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    existing_id: bool = False,
    same_named_monster: bool = False,
) -> dict[str, Any]:
    """Validate against a live-catalog snapshot, without any writes."""
    expected = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in expected.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("not_a_source_statblock")
    d = MONSTERS[name]
    fields = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["actions"]), tuple(d["legendary"]), tuple(d["traits"]),
    )
    if fields != SEALED[name]:
        raise ValueError("original_source_fields_changed")
    if d["page"] not in (196, 198, 199):
        raise ValueError("outside_statblock_pages")
    hp = HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_hit_dice")
    average, count, sides, sign, modifier = hp.groups()
    bonus = int(modifier or 0) * (-1 if sign == "-" else 1)
    if int(average) != (int(count) * (int(sides) + 1)) // 2 + bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"]) != 6 or any(
        not isinstance(v, int) or not 1 <= v <= 30 for v in d["scores"]
    ):
        raise ValueError("six_ability_scores_invalid")

    attrs = {
        "classe_armatura": d["ac"],
        "punti_ferita": d["hp"],
        "velocita": d["speed"],
        "grado_sfida": d["gs"],
        "caratteristiche": dict(zip(
            ("for", "des", "cos", "int", "sag", "car"),
            (str(v) for v in d["scores"]),
        )),
        "tipo_creatura": d["type"],
        "taglia": d["size"],
        "sottotipo_creatura": d["subtype"],
        "allineamento": d["align"],
        "azioni_nomi_da_completare": list(d["actions"]),
        "azioni_leggendarie_nomi_da_completare": list(d["legendary"]),
        "tratti_nomi_da_completare": list(d["traits"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")

    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    excerpt = (
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    return {
        "id": "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32],
        "name": name,
        "physical_page": d["page"],
        "source_excerpt": excerpt,
        "source_text_checksum": hashlib.sha256(excerpt.encode()).hexdigest(),
        "attributes": deepcopy(attrs),
        "status": "source_checked_essential_statistics_only",
        "writes": 0,
    }
