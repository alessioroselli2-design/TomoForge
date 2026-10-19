"""Source-checked essential monster statblocks, Italian MM pp297-304.

The original owner-provided 353-page PDF was visually inspected at full page
resolution and its SHA-256 matched the active registered source. Names,
CA/HP/HD, speeds, six scores, GS and ability headings were checked.
Complete copyrighted spell/action/trait prose is NOT stored here.
Vampire fighting/caster rules remain variants of one source statblock.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Vampiro":{"page":297,"type":"Non morto","size":"Medio","subtype":"mutaforma","align":"legale malvagio","ac":"16 (armatura naturale)","hp":"144 (17d8 + 68)","speed":"9 m","gs":"13","scores":[18,18,18,17,15,18],"traits":["Mutaforma","Resistenza Leggendaria (3/Giorno)","Fuga Nebbiosa","Rigenerazione","Movimenti del Ragno","Debolezze dei Vampiri"],"actions":["Multiattacco (Solo Forma di Vampiro)","Colpo Senz'Armi (Solo Forma di Vampiro)","Morso (Solo Forma di Pipistrello o di Vampiro)","Fascino","Figli della Notte (1/Giorno)"],"legendary":["Movimento","Colpo Senz'Armi","Morso (Costa 2 Azioni)"],"variants":["Vampiro Combattente (GS 15)","Vampiro Incantatore (GS 15)"]},"Progenie Vampirica":{"page":298,"type":"Non morto","size":"Medio","subtype":"","align":"neutrale malvagio","ac":"15 (armatura naturale)","hp":"82 (11d8 + 33)","speed":"9 m","gs":"5","scores":[16,16,16,11,10,12],"traits":["Rigenerazione","Movimenti del Ragno","Debolezze dei Vampiri"],"actions":["Multiattacco","Artigli","Morso"],"legendary":[],"variants":[]},"Verme Purpureo":{"page":299,"type":"Mostruosità","size":"Mastodontica","subtype":"","align":"senza allineamento","ac":"18 (armatura naturale)","hp":"247 (15d20 + 90)","speed":"15 m, scavare 9 m","gs":"15","scores":[28,7,22,1,8,4],"traits":["Scavatore di Tunnel"],"actions":["Multiattacco","Morso","Pungiglione Caudale"],"legendary":[],"variants":[]},"Vermeiena":{"page":300,"type":"Mostruosità","size":"Grande","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"51 (6d10 + 18)","speed":"9 m, scalare 9 m","gs":"2","scores":[14,13,16,1,12,5],"traits":["Olfatto Acuto","Movimenti del Ragno"],"actions":["Multiattacco","Tentacoli","Morso"],"legendary":[],"variants":[]},"Viverna":{"page":301,"type":"Drago","size":"Grande","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"110 (13d10 + 39)","speed":"6 m, volare 24 m","gs":"6","scores":[19,10,16,5,12,6],"traits":[],"actions":["Multiattacco","Morso","Artigli","Pungiglione"],"legendary":[],"variants":[]},"Wight":{"page":302,"type":"Non morto","size":"Medio","subtype":"","align":"neutrale malvagio","ac":"14 (armatura di cuoio borchiato)","hp":"45 (6d8 + 18)","speed":"9 m","gs":"3","scores":[15,14,16,10,13,15],"traits":["Sensibilità alla Luce del Sole"],"actions":["Multiattacco","Risucchio di Vita","Spada Lunga","Arco Lungo"],"legendary":[],"variants":[]},"Wraith":{"page":303,"type":"Non morto","size":"Medio","subtype":"","align":"neutrale malvagio","ac":"13","hp":"67 (9d8 + 27)","speed":"0 m, volare 18 m (fluttuare)","gs":"5","scores":[6,16,16,12,14,15],"traits":["Movimento Incorporeo","Sensibilità alla Luce del Sole"],"actions":["Risucchio di Vita","Creare Spettro"],"legendary":[],"variants":[]},"Xorn":{"page":304,"type":"Elementale","size":"Medio","subtype":"","align":"neutrale","ac":"19 (armatura naturale)","hp":"73 (7d8 + 42)","speed":"6 m, scavare 6 m","gs":"5","scores":[17,10,22,11,10,11],"traits":["Scivolare nella Terra","Mimetismo nella Pietra","Percezione dei Tesori"],"actions":["Multiattacco","Artigli","Morso"],"legendary":[],"variants":[]}}''')
SEALED = {name: (
 d["page"],d["type"],d["size"],d["subtype"],d["align"],d["ac"],
 d["hp"],d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),
 tuple(d["actions"]),tuple(d["legendary"]),tuple(d["variants"]),
) for name,d in _SOURCE.items()}
MONSTERS = deepcopy(_SOURCE)
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")


def audit(name: str, catalog: dict[str, Any] | None, existing_id: bool = False,
          same_named_monster: bool = False) -> dict[str, Any]:
    expected = {
        "logical_source_id": SOURCE_ID, "physical_filename": FILENAME,
        "physical_sha256": SHA256, "physical_pages": PAGES,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k,v in expected.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("not_a_source_statblock")
    d = MONSTERS[name]
    fields = (d["page"],d["type"],d["size"],d["subtype"],d["align"],d["ac"],
              d["hp"],d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),
              tuple(d["actions"]),tuple(d["legendary"]),tuple(d["variants"]))
    if fields != SEALED[name] or d["page"] not in range(297,305):
        raise ValueError("source_fields_changed")
    match = HP_RE.fullmatch(d["hp"])
    if not match:
        raise ValueError("invalid_hit_dice")
    avg,count,sides,sign,modifier = match.groups()
    bonus = int(modifier or 0)*(-1 if sign=="-" else 1)
    if int(avg) != int(count)*(int(sides)+1)//2+bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"])!=6 or any(type(x) is not int or not 1<=x<=30 for x in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attrs = {
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],"velocita":d["speed"],
        "grado_sfida":d["gs"],
        "caratteristiche":dict(zip(("for","des","cos","int","sag","car"),
                                   (str(v) for v in d["scores"]))),
        "tipo_creatura":d["type"],"taglia":d["size"],"sottotipo_creatura":d["subtype"],
        "allineamento":d["align"],"tratti_nomi_da_completare":list(d["traits"]),
        "azioni_nomi_da_completare":list(d["actions"]),
        "azioni_leggendarie_nomi_da_completare":list(d["legendary"]),
        "varianti_nomi_da_completare":list(d["variants"]),
        "completezza_scheda":"statistiche_essenziali",
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt = (f"{name}. {d['type']} {d['size']}, {d['align']}. "
               f"Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. "
               f"Velocità {d['speed']}. Sfida {d['gs']}.")
    token = f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {
        "id":"ref_"+hashlib.sha256(token.encode()).hexdigest()[:32],
        "name":name,"physical_page":d["page"],"attributes":deepcopy(attrs),
        "source_excerpt":excerpt,
        "source_text_checksum":hashlib.sha256(excerpt.encode()).hexdigest(),
        "status":"source_checked_essential_statistics_only","writes":0,
    }
