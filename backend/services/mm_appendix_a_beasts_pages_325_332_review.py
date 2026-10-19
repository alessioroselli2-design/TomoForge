"""Source-reviewed Italian MM Appendix A p325–332: twenty new statblocks.

Original private scanned PDF SHA256 b33eb72e5e... visual reviewed per physical
page. Gufo Gigante is on p326, Gorilla Gigante is genuine omitted p325 box.
Eleven named PHB overlaps are excluded, pending full field comparison.
No scans, complete ability prose, or database writes.
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
_SOURCE:dict[str,dict[str,Any]]=json.loads(r'''{"Gorilla":{"page":325,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"12","hp":"19 (3d8 + 6)","speed":"9 m, scalare 9 m","gs":"1/2","scores":[16,14,14,6,12,7],"traits":[],"actions":["Multiattacco","Pugno","Roccia"]},"Gorilla Gigante":{"page":325,"type":"Bestia","size":"Enorme","subtype":"","align":"senza allineamento","ac":"12","hp":"157 (15d12 + 60)","speed":"12 m, scalare 12 m","gs":"7","scores":[23,14,18,7,12,7],"traits":[],"actions":["Multiattacco","Pugno","Roccia"]},"Granchio":{"page":325,"type":"Bestia","size":"Minuscola","subtype":"","align":"senza allineamento","ac":"11 (armatura naturale)","hp":"2 (1d4)","speed":"6 m, nuotare 6 m","gs":"0","scores":[2,11,10,1,8,2],"traits":["Anfibio"],"actions":["Chela"]},"Granchio Gigante":{"page":325,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"15 (armatura naturale)","hp":"13 (3d8)","speed":"9 m, nuotare 9 m","gs":"1/8","scores":[13,15,11,1,9,3],"traits":["Anfibio"],"actions":["Chela"]},"Gufo Gigante":{"page":326,"type":"Bestia","size":"Grande","subtype":"","align":"neutrale","ac":"12","hp":"19 (3d10 + 3)","speed":"1,5 m, volare 18 m","gs":"1/4","scores":[13,15,12,8,13,10],"traits":["Volo Sfuggente","Vista e Udito Acuti"],"actions":["Speroni"]},"Iena":{"page":326,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"11","hp":"5 (1d8 + 1)","speed":"15 m","gs":"0","scores":[11,13,12,2,12,5],"traits":["Tattiche del Branco"],"actions":["Morso"]},"Iena Gigante":{"page":326,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"12","hp":"45 (6d10 + 12)","speed":"15 m","gs":"1","scores":[16,14,14,2,12,7],"traits":["Furia"],"actions":["Morso"]},"Lucertola":{"page":327,"type":"Bestia","size":"Minuscola","subtype":"","align":"senza allineamento","ac":"10","hp":"2 (1d4)","speed":"6 m, scalare 6 m","gs":"0","scores":[2,11,10,1,8,3],"traits":[],"actions":["Morso"]},"Lucertola Gigante":{"page":327,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"12 (armatura naturale)","hp":"19 (3d10 + 3)","speed":"9 m, scalare 9 m","gs":"1/4","scores":[15,12,13,2,10,5],"traits":[],"actions":["Morso"]},"Lupo Invernale":{"page":328,"type":"Mostruosità","size":"Grande","subtype":"","align":"neutrale malvagio","ac":"13 (armatura naturale)","hp":"75 (10d10 + 20)","speed":"15 m","gs":"3","scores":[18,13,14,7,12,8],"traits":["Olfatto e Udito Acuti","Tattiche del Branco","Mimetismo sulla Neve"],"actions":["Morso","Soffio di Freddo (Ricarica 5-6)"]},"Mammut":{"page":328,"type":"Bestia","size":"Enorme","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"126 (11d12 + 55)","speed":"12 m","gs":"6","scores":[24,9,21,3,11,6],"traits":["Carica Travolgente"],"actions":["Zanne","Calpestare"]},"Millepiedi Gigante":{"page":329,"type":"Bestia","size":"Piccola","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"4 (1d6 + 1)","speed":"9 m, scalare 9 m","gs":"1/4","scores":[5,14,12,1,7,3],"traits":[],"actions":["Morso"]},"Orca Assassina":{"page":329,"type":"Bestia","size":"Enorme","subtype":"","align":"senza allineamento","ac":"12 (armatura naturale)","hp":"90 (12d12 + 12)","speed":"0 m, nuotare 18 m","gs":"3","scores":[19,10,13,3,12,7],"traits":["Senso Radar","Trattenere il Fiato","Udito Acuto"],"actions":["Morso"]},"Orso Polare":{"page":330,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"12 (armatura naturale)","hp":"42 (5d10 + 15)","speed":"12 m, nuotare 9 m","gs":"2","scores":[20,10,16,2,13,7],"traits":["Olfatto Acuto"],"actions":["Multiattacco","Morso","Artigli"]},"Piovra":{"page":330,"type":"Bestia","size":"Piccola","subtype":"","align":"senza allineamento","ac":"12","hp":"3 (1d6)","speed":"1,5 m, nuotare 9 m","gs":"0","scores":[4,15,11,3,10,4],"traits":["Trattenere il Respiro","Mimetismo Acquatico","Respirare Sott'Acqua"],"actions":["Tentacoli","Nube di Inchiostro (Ricarica dopo un Riposo Breve o Lungo)"]},"Piovra Gigante":{"page":331,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"11","hp":"52 (8d10 + 8)","speed":"3 m, nuotare 18 m","gs":"1","scores":[17,13,13,4,10,4],"traits":["Trattenere il Respiro","Mimetismo Acquatico","Respirare Sott'Acqua"],"actions":["Tentacoli","Nube di Inchiostro (Ricarica dopo un Riposo Breve o Lungo)"]},"Pipistrello Gigante":{"page":331,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"13","hp":"22 (4d10)","speed":"3 m, volare 18 m","gs":"1/4","scores":[15,16,11,2,12,6],"traits":["Senso Radar","Udito Acuto"],"actions":["Morso"]},"Pony":{"page":331,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"10","hp":"11 (2d8 + 2)","speed":"12 m","gs":"1/8","scores":[15,10,13,2,11,7],"traits":[],"actions":["Zoccoli"]},"Quipper":{"page":332,"type":"Bestia","size":"Minuscola","subtype":"","align":"senza allineamento","ac":"13","hp":"1 (1d4 - 1)","speed":"0 m, nuotare 12 m","gs":"0","scores":[2,16,9,1,7,2],"traits":["Frenesia di Sangue","Respirare Sott'Acqua"],"actions":["Morso"]},"Ragno":{"page":332,"type":"Bestia","size":"Minuscola","subtype":"","align":"senza allineamento","ac":"12","hp":"1 (1d4 - 1)","speed":"6 m, scalare 6 m","gs":"0","scores":[2,14,8,1,10,2],"traits":["Movimenti del Ragno","Percezione della Ragnatela","Andatura sulla Ragnatela"],"actions":["Morso"]}}''')
PHB_OVERLAPS=frozenset(["Gufo","Leone","Lupo","Lupo Feroce","Mastino","Mulo","Orso Bruno","Orso Nero","Pantera","Pipistrello","Ragno Gigante"])
MONSTERS=deepcopy(_SOURCE)
SEALED={n:(d["page"],d["type"],d["size"],d["align"],d["ac"],d["hp"],
  d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),tuple(d["actions"]))
  for n,d in _SOURCE.items()}
HP_RE=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")

def audit(name:str,catalog:dict[str,Any]|None,existing_id:bool=False,
          same_named_monster:bool=False)->dict[str,Any]:
    expected={"logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
       "physical_sha256":SHA256,"physical_pages":PAGES,"source_status":"active",
       "source_role":"authority","authority_class":"licensed_translation",
       "text_mode":"vision_required"}
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name in PHB_OVERLAPS:
        raise ValueError("existing_phb_monster_needs_full_comparison")
    if name not in SEALED:
        raise ValueError("not_a_statblock")
    d=MONSTERS[name]
    fields=(d["page"],d["type"],d["size"],d["align"],d["ac"],d["hp"],
            d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),tuple(d["actions"]))
    if fields!=SEALED[name] or d["page"] not in range(325,333):
        raise ValueError("source_fields_changed")
    h=HP_RE.fullmatch(d["hp"])
    if not h:
        raise ValueError("invalid_hit_dice")
    avg,count,sides,sign,mod=h.groups()
    bonus=int(mod or 0)*(-1 if sign=="-" else 1)
    if int(avg)!=int(count)*(int(sides)+1)//2+bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"])!=6 or any(type(v) is not int or not 1<=v<=30 for v in d["scores"]):
        raise ValueError("invalid_six_scores")
    attrs={"classe_armatura":d["ac"],"punti_ferita":d["hp"],"velocita":d["speed"],
     "grado_sfida":d["gs"],"caratteristiche":dict(zip(("for","des","cos","int","sag","car"),
     (str(x) for x in d["scores"]))),"tipo_creatura":d["type"],
     "taglia":d["size"],"sottotipo_creatura":"","allineamento":d["align"],
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
