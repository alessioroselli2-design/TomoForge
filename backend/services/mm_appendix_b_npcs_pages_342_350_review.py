"""2014 Italian MM Appendix B NPC original source audit, pp342-350.
Twenty-one independently boxed NPC statblocks read directly from the user
provided 353-page original PDF with SHA256 checked against authority catalog.
Only mathematical core statistics and short ability names are copied. Spell
prepared lists, complete traits and action mechanics are NOT transcribed.
NPCs are DM-usable enemy statblocks, not automatically player characters.
"""
from __future__ import annotations
import hashlib,json,re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags,monster_semantic_numeric_flags

SOURCE_ID="mm_2014_it"
FILENAME="847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256="b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES=353
_SOURCE:dict[str,dict[str,Any]]=json.loads(r'''{"Accolito":{"page":342,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"10","hp":"9 (2d8)","speed":"9 m","gs":"1/4","scores":[10,10,10,10,14,11],"traits":["Incantesimi"],"actions":["Randello"]},"Arcimago":{"page":342,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"12 (15 con armatura magica)","hp":"99 (18d8 + 18)","speed":"9 m","gs":"12","scores":[10,14,12,20,15,16],"traits":["Resistenza alla Magia","Incantesimi"],"actions":["Pugnale"]},"Assassino":{"page":343,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi non buono","ac":"15 (armatura di cuoio borchiato)","hp":"78 (12d8 + 24)","speed":"9 m","gs":"8","scores":[11,16,14,13,11,10],"traits":["Assassinare","Elusione","Attacco Furtivo"],"actions":["Multiattacco","Spada Corta","Balestra Leggera"]},"Bandito":{"page":343,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi non legale","ac":"12 (armatura di cuoio)","hp":"11 (2d8 + 2)","speed":"9 m","gs":"1/8","scores":[11,12,12,10,10,10],"traits":[],"actions":["Scimitarra","Balestra Leggera"]},"Berserker":{"page":344,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi caotico","ac":"13 (armatura di pelle)","hp":"67 (9d8 + 27)","speed":"9 m","gs":"2","scores":[16,12,17,9,11,9],"traits":["Avventato"],"actions":["Ascia Bipenne"]},"Capo dei Banditi":{"page":344,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi non legale","ac":"15 (armatura di cuoio borchiato)","hp":"65 (10d8 + 20)","speed":"9 m","gs":"2","scores":[15,16,14,14,11,14],"traits":[],"actions":["Multiattacco","Scimitarra","Pugnale","Parata (Reazione)"]},"Cavaliere":{"page":344,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"18 (armatura completa)","hp":"52 (8d8 + 16)","speed":"9 m","gs":"3","scores":[16,11,14,11,11,15],"traits":["Impavido"],"actions":["Multiattacco","Spadone","Balestra Pesante","Autorità (Ricarica dopo un Riposo Breve o Lungo)","Parata (Reazione)"]},"Combattente Tribale":{"page":345,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"12 (armatura di pelle)","hp":"11 (2d8 + 2)","speed":"9 m","gs":"1/8","scores":[13,11,12,8,11,8],"traits":["Tattiche del Branco"],"actions":["Lancia"]},"Cultista":{"page":345,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi non buono","ac":"12 (armatura di cuoio)","hp":"9 (2d8)","speed":"9 m","gs":"1/8","scores":[11,12,10,10,11,10],"traits":["Devozione Oscura"],"actions":["Scimitarra"]},"Cultista Fanatico":{"page":346,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi non buono","ac":"13 (armatura di cuoio)","hp":"33 (6d8 + 6)","speed":"9 m","gs":"2","scores":[11,14,12,10,13,14],"traits":["Devozione Oscura","Incantesimi"],"actions":["Multiattacco","Pugnale"]},"Druido":{"page":346,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"11 (16 con pelle coriacea)","hp":"27 (5d8 + 5)","speed":"9 m","gs":"2","scores":[10,12,13,12,15,11],"traits":["Incantesimi"],"actions":["Bastone Ferrato"]},"Esploratore":{"page":347,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"13 (armatura di cuoio)","hp":"16 (3d8 + 3)","speed":"9 m","gs":"1/2","scores":[11,14,12,11,13,11],"traits":["Udito e Vista Acuti"],"actions":["Multiattacco","Spada Corta","Arco Lungo"]},"Gladiatore":{"page":347,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"16 (armatura di cuoio borchiato, scudo)","hp":"112 (15d8 + 45)","speed":"9 m","gs":"5","scores":[18,15,16,10,12,15],"traits":["Impavido","Bruto"],"actions":["Multiattacco","Lancia","Scudo da Sfondamento","Parata (Reazione)"]},"Guardia":{"page":348,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"16 (giaco di maglia, scudo)","hp":"11 (2d8 + 2)","speed":"9 m","gs":"1/8","scores":[13,12,12,10,11,10],"traits":[],"actions":["Lancia"]},"Mago":{"page":348,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"12 (15 con armatura magica)","hp":"40 (9d8)","speed":"9 m","gs":"6","scores":[9,14,11,17,12,11],"traits":["Incantesimi"],"actions":["Pugnale"]},"Malvivente":{"page":348,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi non buono","ac":"11 (armatura di cuoio)","hp":"32 (5d8 + 10)","speed":"9 m","gs":"1/2","scores":[15,11,14,10,10,11],"traits":["Tattiche del Branco"],"actions":["Multiattacco","Mazza","Balestra Pesante"]},"Nobile":{"page":349,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"15 (corazza di piastre)","hp":"9 (2d8)","speed":"9 m","gs":"1/8","scores":[11,12,11,12,14,16],"traits":[],"actions":["Stocco","Parata (Reazione)"]},"Popolano":{"page":349,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"10","hp":"4 (1d8)","speed":"9 m","gs":"0","scores":[10,10,10,10,10,10],"traits":[],"actions":["Randello"]},"Sacerdote":{"page":350,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"13 (giaco di maglia)","hp":"27 (5d8 + 5)","speed":"7,5 m","gs":"2","scores":[10,10,12,13,16,13],"traits":["Eminenza Divina","Incantesimi"],"actions":["Mazza"]},"Spia":{"page":350,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"12","hp":"27 (6d8)","speed":"9 m","gs":"1","scores":[10,15,10,12,14,16],"traits":["Azione Scaltra","Attacco Furtivo"],"actions":["Multiattacco","Spada Corta","Balestra a Mano"]},"Veterano":{"page":350,"type":"Umanoide","size":"Medio","subtype":"qualsiasi razza","align":"qualsiasi","ac":"17 (corazza a strisce)","hp":"58 (9d8 + 18)","speed":"9 m","gs":"3","scores":[16,13,14,10,11,10],"traits":[],"actions":["Multiattacco","Spada Lunga","Spada Corta","Balestra Pesante"]}}''')
MONSTERS=deepcopy(_SOURCE)
SEALED={n:(d["page"],d["type"],d["size"],d["subtype"],d["align"],d["ac"],
d["hp"],d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),tuple(d["actions"]))
for n,d in _SOURCE.items()}
HP_RE=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")

def audit(name:str,catalog:dict[str,Any]|None,existing_id:bool=False,
same_named_monster:bool=False)->dict[str,Any]:
    required={"logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
      "physical_sha256":SHA256,"physical_pages":PAGES,"source_status":"active",
      "source_role":"authority","authority_class":"licensed_translation",
      "text_mode":"vision_required"}
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in required.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name not in SEALED:
        raise ValueError("not_a_source_npc_statblock")
    d=MONSTERS[name]
    fields=(d["page"],d["type"],d["size"],d["subtype"],d["align"],d["ac"],
      d["hp"],d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),tuple(d["actions"]))
    if fields!=SEALED[name] or d["page"] not in range(342,351):
        raise ValueError("source_fields_modified")
    m=HP_RE.fullmatch(d["hp"])
    if m is None:
        raise ValueError("bad_hit_dice")
    avg,count,sides,sign,mod=m.groups()
    bonus=int(mod or 0)*(-1 if sign=="-" else 1)
    if int(avg)!=int(count)*(int(sides)+1)//2+bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"])!=6 or any(type(v) is not int or not 1<=v<=30 for v in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attrs={"classe_armatura":d["ac"],"punti_ferita":d["hp"],"velocita":d["speed"],
      "grado_sfida":d["gs"],"caratteristiche":dict(zip(("for","des","cos","int","sag","car"),(str(v) for v in d["scores"]))),
      "tipo_creatura":d["type"],"taglia":d["size"],"sottotipo_creatura":d["subtype"],
      "allineamento":d["align"],"tratti_nomi_da_completare":list(d["traits"]),
      "azioni_nomi_da_completare":list(d["actions"]),
      "azioni_leggendarie_nomi_da_completare":[],"completezza_scheda":"statistiche_essenziali"}
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt=f"{name}. {d['type']} {d['size']}, {d['align']}. Classe Armatura {d['ac']}. Punti Ferita {d['hp']}. Velocità {d['speed']}. Sfida {d['gs']}."
    token=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {"id":"ref_"+hashlib.sha256(token.encode()).hexdigest()[:32],
      "name":name,"physical_page":d["page"],"attributes":deepcopy(attrs),
      "source_excerpt":excerpt,"source_text_checksum":hashlib.sha256(excerpt.encode()).hexdigest(),
      "status":"source_checked_essential_statistics_only","writes":0}
