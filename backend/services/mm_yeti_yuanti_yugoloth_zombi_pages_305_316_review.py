"""Visual-source audit Italian 2014 MM pp305–316, 11 unique blocks.

All page images inspected at original source resolution with SHA-256 match.
Physical p316 Zombi is a cross-source overlap with PHB original; no duplicate
monster record. Yuan-Ti Nefasto 3 body types belong to ONE boxed statblock.
Pages 307,311,312,315 contain descriptive content not separate statblocks.
Only essential stats and short trait/action names, not complete licensed text.
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
_SOURCE: dict[str, dict[str, Any]] = json.loads(r'''{"Yeti":{"page":305,"type":"Mostruosità","size":"Grande","subtype":"","align":"caotico malvagio","ac":"12 (armatura naturale)","hp":"51 (6d10 + 18)","speed":"12 m, scalare 12 m","gs":"3","scores":[18,13,16,8,12,7],"traits":["Paura del Fuoco","Olfatto Acuto","Mimetismo sulla Neve"],"actions":["Multiattacco","Artigli","Sguardo Agghiacciante"]},"Yeti Abominevole":{"page":306,"type":"Mostruosità","size":"Enorme","subtype":"","align":"caotico malvagio","ac":"15 (armatura naturale)","hp":"137 (11d12 + 66)","speed":"12 m, scalare 12 m","gs":"9","scores":[24,10,22,9,13,9],"traits":["Paura del Fuoco","Olfatto Acuto","Mimetismo sulla Neve"],"actions":["Multiattacco","Artigli","Sguardo Agghiacciante","Soffio di Freddo (Ricarica 6)"]},"Yuan-Ti Abominio":{"page":308,"type":"Mostruosità","size":"Grande","subtype":"mutaforma, yuan-ti","align":"neutrale malvagio","ac":"15 (armatura naturale)","hp":"127 (15d10 + 45)","speed":"12 m","gs":"7","scores":[19,16,17,17,15,18],"traits":["Mutaforma","Incantesimi Innati (Solo Forma di Abominio)","Resistenza alla Magia"],"actions":["Multiattacco (Solo Forma di Abominio)","Morso","Stritolare","Scimitarra (Solo Forma di Abominio)","Arco Lungo (Solo Forma di Abominio)"]},"Yuan-Ti Nefasto":{"page":309,"type":"Mostruosità","size":"Medio","subtype":"mutaforma, yuan-ti","align":"neutrale malvagio","ac":"12","hp":"66 (12d8 + 12)","speed":"9 m","gs":"3","scores":[16,14,13,14,12,16],"traits":["Mutaforma","Incantesimi Innati (Solo Forma di Yuan-ti)","Resistenza alla Magia","Tipo di Nefasto"],"actions":["Tipo 1: Multiattacco, Morso, Scimitarra, Arco Lungo","Tipo 2: Multiattacco, Morso","Tipo 3: Multiattacco, Morso, Stritolare, Scimitarra, Arco Lungo"]},"Yuan-Ti Sanguepuro":{"page":310,"type":"Umanoide","size":"Medio","subtype":"yuan-ti","align":"neutrale malvagio","ac":"11","hp":"40 (9d8)","speed":"9 m","gs":"1","scores":[11,12,11,13,12,14],"traits":["Incantesimi Innati","Resistenza alla Magia"],"actions":["Multiattacco","Scimitarra","Arco Corto"]},"Arcanaloth":{"page":313,"type":"Immondo","size":"Medio","subtype":"yugoloth","align":"neutrale malvagio","ac":"17 (armatura naturale)","hp":"104 (16d8 + 32)","speed":"9 m, volare 9 m","gs":"12","scores":[17,12,14,20,16,17],"traits":["Incantesimi Innati","Resistenza alla Magia","Armi Magiche","Incantesimi"],"actions":["Artigli","Teletrasporto"]},"Mezzoloth":{"page":313,"type":"Immondo","size":"Medio","subtype":"yugoloth","align":"neutrale malvagio","ac":"18 (armatura naturale)","hp":"75 (10d8 + 30)","speed":"12 m","gs":"5","scores":[18,11,16,7,10,11],"traits":["Incantesimi Innati","Resistenza alla Magia","Armi Magiche"],"actions":["Multiattacco","Artigli","Tridente","Teletrasporto"]},"Nycaloth":{"page":314,"type":"Immondo","size":"Grande","subtype":"yugoloth","align":"neutrale malvagio","ac":"18 (armatura naturale)","hp":"123 (13d10 + 52)","speed":"12 m, volare 18 m","gs":"9","scores":[20,11,19,12,10,15],"traits":["Incantesimi Innati","Resistenza alla Magia","Armi Magiche"],"actions":["Multiattacco","Artigli","Ascia Bipenne","Teletrasporto"]},"Ultroloth":{"page":314,"type":"Immondo","size":"Medio","subtype":"yugoloth","align":"neutrale malvagio","ac":"19 (armatura naturale)","hp":"153 (18d8 + 72)","speed":"9 m, volare 18 m","gs":"13","scores":[16,16,18,18,15,19],"traits":["Incantesimi Innati","Resistenza alla Magia","Armi Magiche"],"actions":["Multiattacco","Spada Lunga","Sguardo Ipnotico","Teletrasporto"]},"Zombi Ogre":{"page":316,"type":"Non morto","size":"Grande","subtype":"","align":"neutrale malvagio","ac":"8","hp":"85 (9d10 + 36)","speed":"9 m","gs":"2","scores":[19,6,18,3,6,5],"traits":["Tempra dei Non Morti"],"actions":["Morning Star"]},"Zombi Beholder":{"page":316,"type":"Non morto","size":"Grande","subtype":"","align":"neutrale malvagio","ac":"15 (armatura naturale)","hp":"93 (11d10 + 33)","speed":"0 m, volare 6 m (fluttuare)","gs":"5","scores":[10,8,16,3,8,5],"traits":["Tempra dei Non Morti"],"actions":["Morso","Raggio Oculare"]}}''')
_CROSS_SOURCE_OVERLAP = json.loads(r'''{"name":"Zombi","physical_page":316,"existing_source":"Manuale_del_giocatore__1787259882002.pdf","existing_page":311,"common_core":{"classe_armatura":"8","punti_ferita":"22 (3d8 + 9)","velocita":"6 m"},"decision":"reuse_existing_provisionally_check_full_source_variant_before_consolidation"}''')
MONSTERS = deepcopy(_SOURCE)
CROSS_SOURCE_OVERLAP = deepcopy(_CROSS_SOURCE_OVERLAP)
SEALED = {n:(v["page"],v["type"],v["size"],v["subtype"],v["align"],v["ac"],v["hp"],v["speed"],v["gs"],tuple(v["scores"]),tuple(v["traits"]),tuple(v["actions"])) for n,v in _SOURCE.items()}
HP_RE = re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")


def audit(name: str,catalog:dict[str,Any]|None,existing_id:bool=False,same_named_monster:bool=False)->dict[str,Any]:
    expected={"logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
        "physical_sha256":SHA256,"physical_pages":PAGES,"source_status":"active",
        "source_role":"authority","authority_class":"licensed_translation","text_mode":"vision_required"}
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name=="Zombi":
        raise ValueError("cross_source_duplicate_phb_requires_full_check")
    if name not in SEALED:
        raise ValueError("not_a_statblock")
    d=MONSTERS[name]
    current=(d["page"],d["type"],d["size"],d["subtype"],d["align"],d["ac"],d["hp"],d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),tuple(d["actions"]))
    if current!=SEALED[name] or d["page"] not in (305,306,308,309,310,313,314,316):
        raise ValueError("source_fields_changed")
    hp=HP_RE.fullmatch(d["hp"])
    if hp is None:
        raise ValueError("invalid_hit_dice")
    average,count,sides,sign,modifier=hp.groups()
    bonus=int(modifier or 0)*(-1 if sign=="-" else 1)
    if int(average)!=int(count)*(int(sides)+1)//2+bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"])!=6 or any(type(v) is not int or not 1<=v<=30 for v in d["scores"]):
        raise ValueError("invalid_six_scores")
    attrs={
        "classe_armatura":d["ac"],"punti_ferita":d["hp"],"velocita":d["speed"],"grado_sfida":d["gs"],
        "caratteristiche":dict(zip(("for","des","cos","int","sag","car"),(str(v) for v in d["scores"]))),
        "tipo_creatura":d["type"],"taglia":d["size"],"sottotipo_creatura":d["subtype"],"allineamento":d["align"],
        "tratti_nomi_da_completare":list(d["traits"]),"azioni_nomi_da_completare":list(d["actions"]),
        "azioni_leggendarie_nomi_da_completare":[],"completezza_scheda":"statistiche_essenziali"}
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt=f"{name}. {d['type']} {d['size']}, {d['align']}. Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. Velocità {d['speed']}. Sfida {d['gs']}."
    token=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {"id":"ref_"+hashlib.sha256(token.encode()).hexdigest()[:32],
        "name":name,"physical_page":d["page"],"attributes":deepcopy(attrs),
        "source_excerpt":excerpt,"source_text_checksum":hashlib.sha256(excerpt.encode()).hexdigest(),
        "status":"source_checked_essential_statistics_only","writes":0}
