"""Italian MM pp281–288: six source statblocks and Spritello/Spiritello overlap.

The Monster Manual uses 'Spritello' at physical p281 while PHB lists
'Spiritello' p310 with matching AC, HP and speed. Do not duplicate pending
full-field comparison. Physical p283 is Tarrasque lore not extra statblock.
Only core numerical stats and brief trait/ability names; no PDF or full prose.
"""
from __future__ import annotations
import hashlib
import json
import re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES = 353
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Succube/Incubo":{"page":282,"type":"Immondo","size":"Medio","subtype":"mutaforma","align":"neutrale malvagio","ac":"15 (armatura naturale)","hp":"66 (12d8 + 12)","speed":"9 m, volare 18 m","gs":"4","scores":[8,17,13,15,12,20],"traits":["Legame Telepatico","Mutaforma"],"actions":["Artiglio (Solo Forma di Immondo)","Fascino","Bacio Prosciugante","Forma Eterea"],"legendary":[]},"Tarrasque":{"page":284,"type":"Mostruosità","size":"Mastodontica","subtype":"titano","align":"senza allineamento","ac":"25 (armatura naturale)","hp":"676 (33d20 + 330)","speed":"12 m","gs":"30","scores":[30,11,30,3,11,11],"traits":["Resistenza Leggendaria (3/Giorno)","Resistenza alla Magia","Carapace Riflettente","Mostro da Assedio"],"actions":["Multiattacco","Morso","Artiglio","Corna","Coda","Presenza Terrificante","Inghiottire"],"legendary":["Attacco","Movimento","Masticare (Costa 2 Azioni)"]},"Teschio Infuocato":{"page":285,"type":"Non morto","size":"Minuscolo","subtype":"","align":"neutrale malvagio","ac":"13","hp":"40 (9d4 + 18)","speed":"0 m, volare 12 m (fluttuare)","gs":"4","scores":[1,17,14,16,10,11],"traits":["Illuminazione","Resistenza alla Magia","Ringiovanimento","Incantesimi"],"actions":["Multiattacco","Raggio di Fuoco"],"legendary":[]},"Testuggine Dragona":{"page":286,"type":"Drago","size":"Mastodontica","subtype":"","align":"neutrale","ac":"20 (armatura naturale)","hp":"341 (22d20 + 110)","speed":"6 m, nuotare 12 m","gs":"17","scores":[25,10,20,10,12,12],"traits":["Anfibio"],"actions":["Multiattacco","Morso","Artiglio","Coda","Soffio di Vapore (Ricarica 5-6)"],"legendary":[]},"Thri-Kreen":{"page":287,"type":"Umanoide","size":"Medio","subtype":"thri-kreen","align":"caotico neutrale","ac":"15 (armatura naturale)","hp":"33 (6d8 + 6)","speed":"12 m","gs":"1","scores":[12,15,13,8,12,7],"traits":["Carapace Mimetico","Balzo da Fermo"],"actions":["Multiattacco","Morso","Artigli"],"legendary":[]},"Treant":{"page":288,"type":"Vegetale","size":"Enorme","subtype":"","align":"caotico buono","ac":"16 (armatura naturale)","hp":"138 (12d12 + 60)","speed":"9 m","gs":"9","scores":[23,8,21,12,16,12],"traits":["Falso Aspetto","Mostro da Assedio"],"actions":["Multiattacco","Schianto","Roccia","Animare Alberi (1/Giorno)"],"legendary":[]}}''')
_OVERLAP: dict[str, Any] = json.loads(r'''{"original_name":"Spritello","page":281,"existing_name":"Spiritello","existing_source_key":"Manuale_del_giocatore__1787259882002.pdf","existing_source_page":310,"equal_core_stats":{"classe_armatura":"15 (armatura di cuoio)","punti_ferita":"2 (1d4)","velocita":"3 m, volare 12 m"},"full_field_concordance_confirmed":false,"action":"no_duplicate_pending_full_fields_check"}''')
SEALED = {name: (
    d["page"], d["type"], d["size"], d["subtype"], d["align"],
    d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
    tuple(d["traits"]), tuple(d["actions"]), tuple(d["legendary"]),
) for name,d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)
CROSS_SOURCE_OVERLAP = deepcopy(_OVERLAP)
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")


def audit(
    name: str, catalog: dict[str, Any] | None,
    existing_id: bool = False, same_named_monster: bool = False,
) -> dict[str, Any]:
    expected = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILENAME,
        "physical_sha256": SHA256, "physical_pages": PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name in ("Spritello", "Spiritello"):
        raise ValueError("cross_source_alias_pending_full_comparison")
    if name not in SEALED:
        raise ValueError("not_an_original_statblock")
    d=MONSTERS[name]
    fields=(
        d["page"], d["type"], d["size"], d["subtype"], d["align"],
        d["ac"], d["hp"], d["speed"], d["gs"], tuple(d["scores"]),
        tuple(d["traits"]), tuple(d["actions"]), tuple(d["legendary"]),
    )
    if fields != SEALED[name] or d["page"] not in (282,284,285,286,287,288):
        raise ValueError("source_fields_changed")
    hp = HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_hit_dice")
    avg, count, sides, sign, modifier = hp.groups()
    bonus = int(modifier or 0) * (-1 if sign=="-" else 1)
    if int(avg) != int(count)*(int(sides)+1)//2+bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"])!=6 or any(type(v) is not int or not 1 <= v <= 30 for v in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attrs={
        "classe_armatura":d["ac"], "punti_ferita":d["hp"],
        "velocita":d["speed"], "grado_sfida":d["gs"],
        "caratteristiche":dict(zip(
            ("for","des","cos","int","sag","car"),
            (str(v) for v in d["scores"]),
        )),
        "tipo_creatura":d["type"],"taglia":d["size"],
        "sottotipo_creatura":d["subtype"],"allineamento":d["align"],
        "tratti_nomi_da_completare":list(d["traits"]),
        "azioni_nomi_da_completare":list(d["actions"]),
        "azioni_leggendarie_nomi_da_completare":list(d["legendary"]),
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt=(
        f"{name}. {d['type']} {d['size']}, {d['align']}. "
        f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
        f"Velocità {d['speed']}. Sfida {d['gs']}."
    )
    identity=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {
        "id":"ref_"+hashlib.sha256(identity.encode()).hexdigest()[:32],
        "name":name, "physical_page":d["page"],"attributes":deepcopy(attrs),
        "source_excerpt":excerpt,
        "source_text_checksum":hashlib.sha256(excerpt.encode()).hexdigest(),
        "status":"source_checked_essential_statistics_only","writes":0,
    }
