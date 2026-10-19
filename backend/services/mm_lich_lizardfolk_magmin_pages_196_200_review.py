"""Original Italian MM p196-200: lich, three lizardfolk boxes and magmin.

The owner's full 353-page licensed image-only PDF was reopened and these
original pages individually inspected. Page 197 has Lich lore only; p199
has two independent lizardfolk statblocks. Incantations and legendary
actions are named as incomplete markers, not certified full mechanics.
No PDF bytes or long copyrighted passages committed. No database writes.
"""
from __future__ import annotations

import hashlib
import json
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
_ORIGINAL: dict[str, dict[str, Any]] = json.loads(
    "{\"Lich\":{\"page\":196,\"type\":\"Non morto\",\"size\":\"Medio\",\"subtype\":\"\",\"align\":\"qualsiasi allineamento malvagio\",\"ac\":\"17 (armatura naturale)\",\"hp\":\"135 (18d8 + 54)\",\"speed\":\"9 m\",\"gs\":\"21\",\"scores\":[11,16,16,20,14,16],\"actions\":[\"Tocco Paralizzante\"],\"traits\":[\"Resistenza Leggendaria\",\"Ringiovanimento\",\"Incantesimi\"],\"legendary_actions\":[\"Trucchetto\",\"Tocco Paralizzante\",\"Sguardo Terrificante\",\"Distruggere Vita\"],\"spellcaster_level\":18},\"Lucertoloide\":{\"page\":198,\"type\":\"Umanoide\",\"size\":\"Medio\",\"subtype\":\"lucertoloide\",\"align\":\"neutrale\",\"ac\":\"15 (armatura naturale, scudo)\",\"hp\":\"22 (4d8 + 4)\",\"speed\":\"9 m, nuotare 9 m\",\"gs\":\"1/2\",\"scores\":[15,10,13,7,12,7],\"actions\":[\"Multiattacco\",\"Morso\",\"Randello Pesante\",\"Giavellotto\",\"Scudo Chiodato\"],\"traits\":[\"Trattenere il Respiro\"]},\"Lucertoloide Sciamano\":{\"page\":199,\"type\":\"Umanoide\",\"size\":\"Medio\",\"subtype\":\"lucertoloide\",\"align\":\"neutrale\",\"ac\":\"13 (armatura naturale)\",\"hp\":\"27 (5d8 + 5)\",\"speed\":\"9 m, nuotare 9 m\",\"gs\":\"2\",\"scores\":[15,10,13,10,15,8],\"actions\":[\"Multiattacco\",\"Morso\",\"Artigli\"],\"traits\":[\"Trattenere il Respiro\",\"Incantesimi\",\"Cambiare Forma\"],\"spellcaster_level\":5},\"Re/Regina Lucertola\":{\"page\":199,\"type\":\"Umanoide\",\"size\":\"Medio\",\"subtype\":\"lucertoloide\",\"align\":\"caotico malvagio\",\"ac\":\"15 (armatura naturale)\",\"hp\":\"78 (12d8 + 24)\",\"speed\":\"9 m, nuotare 9 m\",\"gs\":\"4\",\"scores\":[17,12,15,11,11,15],\"actions\":[\"Multiattacco\",\"Morso\",\"Artigli\",\"Tridente\"],\"traits\":[\"Trattenere il Respiro\",\"Trafiggere\"]},\"Magmin\":{\"page\":200,\"type\":\"Elementale\",\"size\":\"Piccolo\",\"subtype\":\"\",\"align\":\"caotico neutrale\",\"ac\":\"14 (armatura naturale)\",\"hp\":\"9 (2d6 + 2)\",\"speed\":\"9 m\",\"gs\":\"1/2\",\"scores\":[7,15,12,8,11,10],\"actions\":[\"Tocco\"],\"traits\":[\"Esplosione Mortale\",\"Illuminazione Fiammeggiante\"]}}"
)
SEALED = {
    name: (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["actions"]), tuple(d["traits"]),
        tuple(d.get("legendary_actions", [])),
        d.get("spellcaster_level"),
    )
    for name, d in _ORIGINAL.items()
}
MONSTERS = deepcopy(_ORIGINAL)


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    existing_monster: bool = False,
) -> dict[str, Any]:
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(key) != val for key, val in required.items()
    ):
        raise ValueError("registered_source_mismatch")
    if existing_monster:
        raise ValueError("duplicate_monster")
    if name not in SEALED:
        raise ValueError("not_an_independent_monster")
    d = MONSTERS[name]
    current = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["actions"]), tuple(d["traits"]),
        tuple(d.get("legendary_actions", [])),
        d.get("spellcaster_level"),
    )
    if current != SEALED[name]:
        raise ValueError("original_source_fields_changed")
    if d["page"] not in (196, 198, 199, 200):
        raise ValueError("outside_original_page_window")
    hit_dice = HP_RE.fullmatch(d["hp"])
    if hit_dice is None:
        raise ValueError("hit_dice_unparseable")
    mean, count, sides, op, diff = hit_dice.groups()
    delta = int(diff or 0) * (-1 if op == "-" else 1)
    if int(mean) != int(count) * (int(sides) + 1) // 2 + delta:
        raise ValueError("incorrect_hit_dice_average")
    if len(d["scores"]) != 6 or any(
        not isinstance(score, int) or not 1 <= score <= 30
        for score in d["scores"]
    ):
        raise ValueError("six_characteristics_invalid")

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
        "allineamento": d["align"],
        "azioni_nomi_da_completare": list(d["actions"]),
        "tratti_nomi_da_completare": list(d["traits"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if d["subtype"]:
        attrs["sottotipo_creatura"] = d["subtype"]
    if d.get("spellcaster_level"):
        attrs["livello_incantatore_da_completare"] = d["spellcaster_level"]
    if d.get("legendary_actions"):
        attrs["azioni_leggendarie_nomi_da_completare"] = list(d["legendary_actions"])
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("semantic_numeric_gate")
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    short = (
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    return {
        "id": "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32],
        "name": name, "physical_page": d["page"],
        "source_excerpt": short,
        "source_text_checksum": hashlib.sha256(short.encode()).hexdigest(),
        "attributes": deepcopy(attrs),
        "status": "source_checked_essential_statistics_only",
        "writes": 0,
    }
