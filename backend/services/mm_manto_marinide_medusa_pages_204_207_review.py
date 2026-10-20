"""Four visual-source-checked Italian MM statblocks, physical pp204–207.

Original licensed 353-page PDF checked against live source catalog SHA256.
Page 208 begins Megera lore/congrega; that sidebar is not an individual
monster statblock. No full action texts/images, no Supabase writes.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Manto Assassino":{"page":204,"type":"Aberrazione","size":"Grande","subtype":"","align":"caotico neutrale","ac":"14 (armatura naturale)","hp":"78 (12d10 + 12)","speed":"3 m, volare 12 m","gs":"8","scores":[17,15,12,13,12,14],"traits":["Trasferire Danni","Falso Aspetto","Sensibilità alla Luce"],"actions":["Multiattacco","Morso","Coda","Gemito","Allucinazioni (Ricarica dopo un Riposo Breve o Lungo)"]},"Mantoscuro":{"page":205,"type":"Mostruosità","size":"Piccolo","subtype":"","align":"senza allineamento","ac":"11","hp":"22 (5d6 + 5)","speed":"3 m, volare 9 m","gs":"1/2","scores":[16,12,13,2,10,5],"traits":["Senso Radar","Falso Aspetto","Aura di Oscurità (1/Giorno)"],"actions":["Schiacciare"]},"Marinide":{"page":206,"type":"Umanoide","size":"Medio","subtype":"marinide","align":"neutrale","ac":"11","hp":"11 (2d8 + 2)","speed":"3 m, nuotare 12 m","gs":"1/8","scores":[10,13,12,11,11,12],"traits":["Anfibio"],"actions":["Lancia"]},"Medusa":{"page":207,"type":"Mostruosità","size":"Medio","subtype":"","align":"legale malvagio","ac":"15 (armatura naturale)","hp":"127 (17d8 + 51)","speed":"9 m","gs":"6","scores":[10,15,16,12,13,15],"traits":["Sguardo Pietrificante"],"actions":["Multiattacco","Chioma di Serpenti","Spada Corta","Arco Lungo"]}}''')
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
    """Run strict statblock evidence gates without database mutations."""
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
    if not isinstance(catalog, dict) or any(
        catalog.get(k) != v for k, v in expected.items()
    ):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("not_a_source_statblock")
    d = MONSTERS[name]
    fields = (
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["actions"]), tuple(d["traits"]),
    )
    if fields != SEALED[name]:
        raise ValueError("original_source_fields_changed")
    if d["page"] not in (204, 205, 206, 207):
        raise ValueError("outside_source_window")
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
