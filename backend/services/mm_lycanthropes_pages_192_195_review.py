"""Five independently boxed Italian MM lycanthropes, physical pp192-195.

Owner-licensed Italian 353-page image-only original directly re-opened and
visually inspected in this task. Each CA/speed may depend on creature form;
the original qualifiers are kept, not collapsed to one numeric value.
This code only audits core stats plus short action/trait labels, not full
actions; it never executes database writes or publishes licensed pages.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(
    "{\"Cinghiale Mannaro\":{\"page\":192,\"type\":\"Umanoide\",\"size\":\"Medio\",\"subtype\":\"umano, mutaforma\",\"align\":\"neutrale malvagio\",\"ac\":\"10 in forma umanoide, 11 (armatura naturale) in forma di cinghiale o ibrida\",\"hp\":\"78 (12d8 + 24)\",\"speed\":\"9 m (12 m in forma di cinghiale)\",\"gs\":\"4\",\"scores\":[17,10,15,10,11,8],\"actions\":[\"Multiattacco\",\"Maglio\",\"Zanne\"],\"traits\":[\"Mutaforma\",\"Carica\",\"Implacabile\"]},\"Orso Mannaro\":{\"page\":193,\"type\":\"Umanoide\",\"size\":\"Medio\",\"subtype\":\"umano, mutaforma\",\"align\":\"neutrale buono\",\"ac\":\"10 in forma umanoide, 11 (armatura naturale) in forma di orso o ibrida\",\"hp\":\"135 (18d8 + 54)\",\"speed\":\"9 m (12 m, scalare 9 m in forma di orso o ibrida)\",\"gs\":\"5\",\"scores\":[19,10,17,11,12,12],\"actions\":[\"Multiattacco\",\"Morso\",\"Artiglio\",\"Ascia Bipenne\"],\"traits\":[\"Mutaforma\",\"Olfatto Acuto\"]},\"Lupo Mannaro\":{\"page\":193,\"type\":\"Umanoide\",\"size\":\"Medio\",\"subtype\":\"umano, mutaforma\",\"align\":\"caotico malvagio\",\"ac\":\"11 in forma umanoide, 12 (armatura naturale) in forma di lupo o ibrida\",\"hp\":\"58 (9d8 + 18)\",\"speed\":\"9 m (12 m in forma di lupo)\",\"gs\":\"3\",\"scores\":[15,13,14,10,11,10],\"actions\":[\"Multiattacco\",\"Morso\",\"Artigli\",\"Lancia\"],\"traits\":[\"Mutaforma\",\"Olfatto e Udito Acuti\"]},\"Tigre Mannara\":{\"page\":194,\"type\":\"Umanoide\",\"size\":\"Medio\",\"subtype\":\"umano, mutaforma\",\"align\":\"neutrale\",\"ac\":\"12\",\"hp\":\"120 (16d8 + 48)\",\"speed\":\"9 m (12 m in forma di tigre)\",\"gs\":\"4\",\"scores\":[17,15,16,10,13,11],\"actions\":[\"Multiattacco\",\"Morso\",\"Artigli\",\"Scimitarra\",\"Arco Lungo\"],\"traits\":[\"Mutaforma\",\"Olfatto e Udito Acuti\",\"Balzo\"]},\"Topo Mannaro\":{\"page\":195,\"type\":\"Umanoide\",\"size\":\"Medio\",\"subtype\":\"umano, mutaforma\",\"align\":\"legale malvagio\",\"ac\":\"12\",\"hp\":\"33 (6d8 + 6)\",\"speed\":\"9 m\",\"gs\":\"2\",\"scores\":[10,15,12,11,10,8],\"actions\":[\"Multiattacco\",\"Morso\",\"Spada Corta\",\"Balestra a Mano\"],\"traits\":[\"Mutaforma\",\"Olfatto Acuto\"]}}"
)
SEALED = {
    name: (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["actions"]), tuple(d["traits"]),
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
    expected_catalog = {
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
        catalog.get(k) != v for k, v in expected_catalog.items()
    ):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("no_independent_lycanthrope_statblock")
    d = MONSTERS[name]
    fields = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["actions"]), tuple(d["traits"]),
    )
    if fields != SEALED[name]:
        raise ValueError("original_source_fields_changed")
    if d["page"] not in (192, 193, 194, 195):
        raise ValueError("outside_source_page_window")
    hp = HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_hit_dice")
    avg, n, sides, sign, modifier = hp.groups()
    bonus = int(modifier or 0) * (-1 if sign == "-" else 1)
    if int(avg) != int(n) * (int(sides) + 1) // 2 + bonus:
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
        "tratti_nomi_da_completare": list(d["traits"]),
        "completezza_scheda": "statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    excerpt = (
        f"{name}. {d['type']} {d['size']} ({d['subtype']}), {d['align']}. "
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
