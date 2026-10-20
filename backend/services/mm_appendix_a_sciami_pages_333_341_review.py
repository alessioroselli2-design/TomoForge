"""Direct original-source essential stats audit, Italian MM Appendix A p333–341.

Twenty-six independent new source statblocks visually confirmed from private
353-page source, six already-PHB source overlaps excluded. The 'Topo Gigante
Contagioso' and insect swarm subtypes are variants, not new boxed monsters.
Only essential stats and short action labels are committed; NEVER original scans
or complete licensed ability descriptions, and zero Supabase writes.
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
_SOURCE:dict[str,dict[str,Any]]=json.loads(r'''{"Ragno Lupo Gigante":{"page":333,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"13","hp":"11 (2d8 + 2)","speed":"12 m, scalare 12 m","gs":"1/4","scores":[12,16,13,3,12,4],"traits":["Movimenti del Ragno","Percezione della Ragnatela","Andatura sulla Ragnatela"],"actions":["Morso"]},"Ragno-Fase":{"page":333,"type":"Mostruosità","size":"Grande","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"32 (5d10 + 5)","speed":"9 m, scalare 9 m","gs":"3","scores":[15,15,12,6,10,6],"traits":["Transizione Eterea","Movimenti del Ragno","Andatura sulla Ragnatela"],"actions":["Morso"]},"Rana Gigante":{"page":334,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"11","hp":"18 (4d8)","speed":"9 m, nuotare 9 m","gs":"1/4","scores":[12,13,11,2,10,3],"traits":["Anfibio","Balzo da Fermo"],"actions":["Morso","Inghiottire"]},"Rinoceronte":{"page":334,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"11 (armatura naturale)","hp":"45 (6d10 + 12)","speed":"12 m","gs":"2","scores":[21,8,15,2,12,6],"traits":["Carica"],"actions":["Incornata"]},"Rospo Gigante":{"page":334,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"11","hp":"39 (6d10 + 6)","speed":"6 m, nuotare 12 m","gs":"1","scores":[15,13,13,2,10,3],"traits":["Anfibio","Balzo da Fermo"],"actions":["Morso","Inghiottire"]},"Scarabeo di Fuoco Gigante":{"page":335,"type":"Bestia","size":"Piccola","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"4 (1d6 + 1)","speed":"9 m","gs":"0","scores":[8,10,12,1,7,3],"traits":["Illuminazione"],"actions":["Morso"]},"Sciacallo":{"page":335,"type":"Bestia","size":"Piccola","subtype":"","align":"senza allineamento","ac":"12","hp":"3 (1d6)","speed":"12 m","gs":"0","scores":[8,15,11,3,12,6],"traits":["Olfatto e Udito Acuti","Tattiche del Branco"],"actions":["Morso"]},"Sciame di Corvi":{"page":335,"type":"Sciame di bestie","size":"Medio","subtype":"bestie Minuscole","align":"senza allineamento","ac":"12","hp":"24 (7d8 - 7)","speed":"3 m, volare 15 m","gs":"1/4","scores":[6,14,8,3,12,6],"traits":["Sciame"],"actions":["Becchi"]},"Sciame di Insetti":{"page":335,"type":"Sciame di bestie","size":"Medio","subtype":"bestie Minuscole","align":"senza allineamento","ac":"12 (armatura naturale)","hp":"22 (5d8)","speed":"6 m, scalare 6 m","gs":"1/2","scores":[3,13,10,1,7,1],"traits":["Sciame"],"actions":["Morsi"]},"Sciame di Pipistrelli":{"page":336,"type":"Sciame di bestie","size":"Medio","subtype":"bestie Minuscole","align":"senza allineamento","ac":"12","hp":"22 (5d8)","speed":"0 m, volare 9 m","gs":"1/4","scores":[5,15,10,2,12,4],"traits":["Senso Radar","Udito Acuto","Sciame"],"actions":["Morsi"]},"Sciame di Quipper":{"page":336,"type":"Sciame di bestie","size":"Medio","subtype":"bestie Minuscole","align":"senza allineamento","ac":"13","hp":"28 (8d8 - 8)","speed":"0 m, nuotare 12 m","gs":"1","scores":[13,16,9,1,7,2],"traits":["Frenesia di Sangue","Sciame","Respirare Sott'Acqua"],"actions":["Morsi"]},"Sciame di Serpenti Velenosi":{"page":336,"type":"Sciame di bestie","size":"Medio","subtype":"bestie Minuscole","align":"senza allineamento","ac":"14","hp":"36 (8d8)","speed":"9 m, nuotare 9 m","gs":"2","scores":[8,18,11,1,10,3],"traits":["Sciame"],"actions":["Morsi"]},"Sciame di Topi":{"page":337,"type":"Sciame di bestie","size":"Medio","subtype":"bestie Minuscole","align":"senza allineamento","ac":"10","hp":"24 (7d8 - 7)","speed":"9 m","gs":"1/4","scores":[9,11,9,2,10,3],"traits":["Olfatto Acuto","Sciame"],"actions":["Morsi"]},"Scorpione":{"page":337,"type":"Bestia","size":"Minuscola","subtype":"","align":"senza allineamento","ac":"11 (armatura naturale)","hp":"1 (1d4 - 1)","speed":"3 m","gs":"0","scores":[2,11,8,1,8,2],"traits":[],"actions":["Pungiglione"]},"Scorpione Gigante":{"page":337,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"15 (armatura naturale)","hp":"52 (7d10 + 14)","speed":"12 m","gs":"3","scores":[15,13,15,1,9,3],"traits":[],"actions":["Multiattacco","Artigli","Pungiglione"]},"Serpente Stritolatore Gigante":{"page":338,"type":"Bestia","size":"Enorme","subtype":"","align":"senza allineamento","ac":"12","hp":"60 (8d12 + 8)","speed":"9 m, nuotare 9 m","gs":"2","scores":[19,14,12,1,10,3],"traits":[],"actions":["Morso","Stritolare"]},"Serpente Velenoso Gigante":{"page":338,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"14","hp":"11 (2d8 + 2)","speed":"9 m, nuotare 9 m","gs":"1/4","scores":[10,18,13,2,10,3],"traits":[],"actions":["Morso"]},"Serpente Volante":{"page":338,"type":"Bestia","size":"Minuscola","subtype":"","align":"senza allineamento","ac":"14","hp":"5 (2d4)","speed":"9 m, nuotare 9 m, volare 18 m","gs":"1/8","scores":[4,18,11,2,12,5],"traits":["Volo Sfuggente"],"actions":["Morso"]},"Squalo Cacciatore":{"page":338,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"12 (armatura naturale)","hp":"45 (6d10 + 12)","speed":"0 m, nuotare 12 m","gs":"2","scores":[18,13,15,1,10,4],"traits":["Frenesia di Sangue","Respirare Sott'Acqua"],"actions":["Morso"]},"Squalo Gigante":{"page":339,"type":"Bestia","size":"Enorme","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"126 (11d12 + 55)","speed":"0 m, nuotare 15 m","gs":"5","scores":[23,11,21,1,10,5],"traits":["Frenesia di Sangue","Respirare Sott'Acqua"],"actions":["Morso"]},"Tasso":{"page":339,"type":"Bestia","size":"Minuscola","subtype":"","align":"senza allineamento","ac":"10","hp":"3 (1d4 + 1)","speed":"6 m, scavare 1,5 m","gs":"0","scores":[4,11,12,2,12,5],"traits":["Olfatto Acuto"],"actions":["Morso"]},"Tasso Gigante":{"page":339,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"10","hp":"13 (2d8 + 4)","speed":"9 m, scavare 3 m","gs":"1/4","scores":[13,10,15,2,12,5],"traits":["Olfatto Acuto"],"actions":["Multiattacco","Morso","Artigli"]},"Tigre dai Denti a Sciabola":{"page":340,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"12","hp":"52 (7d10 + 14)","speed":"12 m","gs":"2","scores":[18,14,15,3,12,8],"traits":["Olfatto Acuto","Balzo"],"actions":["Morso","Artigli"]},"Topo Gigante":{"page":340,"type":"Bestia","size":"Piccola","subtype":"","align":"senza allineamento","ac":"12","hp":"7 (2d6)","speed":"9 m","gs":"1/8","scores":[7,15,11,2,10,4],"traits":["Olfatto Acuto","Tattiche del Branco"],"actions":["Morso"]},"Vespa Gigante":{"page":341,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"12","hp":"13 (3d8)","speed":"3 m, volare 15 m","gs":"1/2","scores":[10,14,10,1,10,3],"traits":[],"actions":["Pungiglione"]},"Worg":{"page":341,"type":"Mostruosità","size":"Grande","subtype":"","align":"neutrale malvagio","ac":"13 (armatura naturale)","hp":"26 (4d10 + 4)","speed":"15 m","gs":"1/2","scores":[16,13,13,7,11,8],"traits":["Olfatto e Udito Acuti"],"actions":["Morso"]}}''')
PHB_OVERLAPS=frozenset(["Rana","Serpente Stritolatore","Serpente Velenoso","Squalo Tropicale","Tigre","Topo"])
MONSTERS=deepcopy(_SOURCE)
SEALED={n:(d["page"],d["type"],d["size"],d["subtype"],d["align"],d["ac"],d["hp"],
  d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),tuple(d["actions"]))
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
    if name in PHB_OVERLAPS:
        raise ValueError("existing_phb_monster_requires_full_comparison")
    if name not in SEALED:
        raise ValueError("not_a_source_statblock")
    d=MONSTERS[name]
    fields=(d["page"],d["type"],d["size"],d["subtype"],d["align"],d["ac"],d["hp"],
        d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),tuple(d["actions"]))
    if fields!=SEALED[name] or d["page"] not in range(333,342):
        raise ValueError("original_source_fields_changed")
    hp=HP_RE.fullmatch(d["hp"])
    if not hp:
        raise ValueError("invalid_hit_dice")
    avg,count,sides,sign,mod=hp.groups()
    bonus=int(mod or 0)*(-1 if sign=="-" else 1)
    if int(avg)!=int(count)*(int(sides)+1)//2+bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"])!=6 or any(type(v) is not int or not 1<=v<=30 for v in d["scores"]):
        raise ValueError("six_ability_scores_invalid")
    attrs={"classe_armatura":d["ac"],"punti_ferita":d["hp"],"velocita":d["speed"],
      "grado_sfida":d["gs"],"caratteristiche":dict(zip(("for","des","cos","int","sag","car"),(str(x) for x in d["scores"]))),
      "tipo_creatura":d["type"],"taglia":d["size"],"sottotipo_creatura":d["subtype"],
      "allineamento":d["align"],"tratti_nomi_da_completare":list(d["traits"]),
      "azioni_nomi_da_completare":list(d["actions"]),
      "azioni_leggendarie_nomi_da_completare":[],"completezza_scheda":"statistiche_essenziali"}
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt=(f"{name}. {d['type']} {d['size']}, {d['align']}. Classe Armatura {d['ac']}. "
             f"Punti Ferita {d['hp']}. Velocità {d['speed']}. Sfida {d['gs']}.")
    token=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {"id":"ref_"+hashlib.sha256(token.encode()).hexdigest()[:32],
      "name":name,"physical_page":d["page"],"attributes":deepcopy(attrs),
      "source_excerpt":excerpt,"source_text_checksum":hashlib.sha256(excerpt.encode()).hexdigest(),
      "status":"source_checked_essential_statistics_only","writes":0}
