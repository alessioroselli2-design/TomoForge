"""Italian MM Appendix A, physical pp317–324: 24 new boxed statblocks.

Independently visually checked original scanned private authority at full
resolution; 8 exact-name PHB overlaps are excluded from new records pending
full-field/source-page equivalence. Body actions/traits are still title-only.
No PDF, images or complete copyrighted rule passages are stored here.
"""
from __future__ import annotations
import hashlib
import json
import re
from copy import deepcopy
from typing import Any
from services.ocr_semantic_gates import monster_identity_sanity_flags, monster_semantic_numeric_flags

SOURCE_ID="mm_2014_it"
FILENAME="847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256="b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES=353
_SOURCE:dict[str,dict[str,Any]]=json.loads(r'''{"Albero Risvegliato":{"page":317,"type":"Vegetale","size":"Enorme","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"59 (7d12 + 14)","speed":"6 m","gs":"2","scores":[19,6,15,10,10,7],"traits":["Falso Aspetto"],"actions":["Schianto"]},"Alce":{"page":317,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"10","hp":"13 (2d10 + 2)","speed":"15 m","gs":"1/4","scores":[16,10,12,2,10,6],"traits":["Carica"],"actions":["Sfondamento","Zoccoli"]},"Alce Gigante":{"page":317,"type":"Bestia","size":"Enorme","subtype":"","align":"senza allineamento","ac":"14 (armatura naturale)","hp":"42 (5d12 + 10)","speed":"18 m","gs":"2","scores":[19,16,14,7,14,10],"traits":["Carica"],"actions":["Sfondamento","Zoccoli"]},"Aquila":{"page":317,"type":"Bestia","size":"Piccola","subtype":"","align":"senza allineamento","ac":"12","hp":"3 (1d6)","speed":"3 m, volare 18 m","gs":"0","scores":[6,15,10,2,14,7],"traits":["Vista Acuta"],"actions":["Speroni"]},"Avvoltoio":{"page":318,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"10","hp":"5 (1d8 + 1)","speed":"3 m, volare 15 m","gs":"0","scores":[7,10,13,2,12,4],"traits":["Olfatto e Vista Acuti","Tattiche del Branco"],"actions":["Becco"]},"Avvoltoio Gigante":{"page":318,"type":"Bestia","size":"Grande","subtype":"","align":"neutrale malvagio","ac":"10","hp":"22 (3d10 + 6)","speed":"3 m, volare 18 m","gs":"1","scores":[15,10,15,6,12,7],"traits":["Olfatto e Vista Acuti","Tattiche del Branco"],"actions":["Multiattacco","Becco","Speroni"]},"Babbuino":{"page":318,"type":"Bestia","size":"Piccola","subtype":"","align":"senza allineamento","ac":"12","hp":"3 (1d6)","speed":"9 m, scalare 9 m","gs":"0","scores":[8,14,11,4,12,6],"traits":["Tattiche del Branco"],"actions":["Morso"]},"Beccoaguzzo":{"page":319,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"11","hp":"19 (3d10 + 3)","speed":"15 m","gs":"1/4","scores":[14,12,12,2,10,5],"traits":[],"actions":["Becco"]},"Cammello":{"page":319,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"9","hp":"15 (2d10 + 4)","speed":"15 m","gs":"1/8","scores":[16,8,14,2,8,5],"traits":[],"actions":["Morso"]},"Cane della Morte":{"page":319,"type":"Mostruosità","size":"Media","subtype":"","align":"neutrale malvagio","ac":"12","hp":"39 (6d8 + 12)","speed":"12 m","gs":"1","scores":[15,14,14,3,13,6],"traits":["Due Teste"],"actions":["Multiattacco","Morso"]},"Cane Intermittente":{"page":320,"type":"Folletto","size":"Medio","subtype":"","align":"legale buono","ac":"13","hp":"22 (4d8 + 4)","speed":"12 m","gs":"1/4","scores":[12,17,12,10,13,11],"traits":["Olfatto e Udito Acuti"],"actions":["Morso","Teletrasporto (Ricarica 4-6)"]},"Capra":{"page":320,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"10","hp":"4 (1d8)","speed":"12 m","gs":"0","scores":[12,10,11,2,10,5],"traits":["Carica","Ben Piantato"],"actions":["Sfondamento"]},"Capra Gigante":{"page":320,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"11 (armatura naturale)","hp":"19 (3d10 + 3)","speed":"12 m","gs":"1/2","scores":[17,11,12,3,12,6],"traits":["Carica","Ben Piantato"],"actions":["Sfondamento"]},"Cavallo da Tiro":{"page":321,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"10","hp":"19 (3d10 + 3)","speed":"12 m","gs":"1/4","scores":[18,10,12,2,11,7],"traits":[],"actions":["Zoccoli"]},"Cavalluccio Marino":{"page":321,"type":"Bestia","size":"Minuscola","subtype":"","align":"senza allineamento","ac":"11","hp":"1 (1d4 - 1)","speed":"0 m, nuotare 6 m","gs":"0","scores":[1,12,8,1,10,2],"traits":["Respirare Sott'Acqua"],"actions":[]},"Cavalluccio Marino Gigante":{"page":321,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"13 (armatura naturale)","hp":"16 (3d10)","speed":"0 m, nuotare 12 m","gs":"1/2","scores":[12,15,11,2,12,5],"traits":["Carica","Respirare Sott'Acqua"],"actions":["Sfondamento"]},"Cespuglio Risvegliato":{"page":322,"type":"Vegetale","size":"Piccolo","subtype":"","align":"senza allineamento","ac":"9","hp":"10 (3d6)","speed":"6 m","gs":"0","scores":[3,8,11,10,10,6],"traits":["Falso Aspetto"],"actions":["Graffiare"]},"Cinghiale Gigante":{"page":322,"type":"Bestia","size":"Grande","subtype":"","align":"senza allineamento","ac":"12 (armatura naturale)","hp":"42 (5d10 + 15)","speed":"12 m","gs":"2","scores":[17,10,16,2,7,5],"traits":["Carica","Implacabile"],"actions":["Zanne"]},"Coccodrillo Gigante":{"page":323,"type":"Bestia","size":"Enorme","subtype":"","align":"senza allineamento","ac":"14 (armatura naturale)","hp":"85 (9d12 + 27)","speed":"9 m, nuotare 15 m","gs":"5","scores":[21,9,17,2,10,7],"traits":["Trattenere il Respiro"],"actions":["Multiattacco","Morso","Coda"]},"Daino":{"page":323,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"13","hp":"4 (1d8)","speed":"15 m","gs":"0","scores":[11,16,11,2,14,5],"traits":[],"actions":["Morso"]},"Elefante":{"page":323,"type":"Bestia","size":"Enorme","subtype":"","align":"senza allineamento","ac":"12 (armatura naturale)","hp":"76 (8d12 + 24)","speed":"12 m","gs":"4","scores":[22,9,17,3,11,6],"traits":["Carica Travolgente"],"actions":["Zanne","Calpestare"]},"Faina":{"page":324,"type":"Bestia","size":"Minuscola","subtype":"","align":"senza allineamento","ac":"13","hp":"1 (1d4 - 1)","speed":"9 m","gs":"0","scores":[3,16,8,2,12,3],"traits":["Olfatto e Udito Acuti"],"actions":["Morso"]},"Faina Gigante":{"page":324,"type":"Bestia","size":"Media","subtype":"","align":"senza allineamento","ac":"13","hp":"9 (2d8)","speed":"12 m","gs":"1/8","scores":[11,16,10,4,12,5],"traits":["Olfatto e Udito Acuti"],"actions":["Morso"]},"Falco di Sangue":{"page":324,"type":"Bestia","size":"Piccola","subtype":"","align":"senza allineamento","ac":"12","hp":"7 (2d6)","speed":"3 m, volare 18 m","gs":"1/8","scores":[6,14,10,3,14,5],"traits":["Vista Acuta","Tattiche del Branco"],"actions":["Becco"]}}''')
EXISTING_CROSS_SOURCE_NAMES=frozenset(["Aquila Gigante","Cavallo da Galoppo","Cavallo da Guerra","Cinghiale","Coccodrillo","Corvo","Falco","Gatto"])
MONSTERS=deepcopy(_SOURCE)
SEALED={n:(d["page"],d["type"],d["size"],d["align"],d["ac"],d["hp"],
    d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),tuple(d["actions"]))
    for n,d in _SOURCE.items()}
HP_RE=re.compile(r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$")

def audit(name:str,catalog:dict[str,Any]|None,existing_id:bool=False,
          same_named_monster:bool=False)->dict[str,Any]:
    expected={"logical_source_id":SOURCE_ID,"physical_filename":FILENAME,
        "physical_sha256":SHA256,"physical_pages":PAGES,"source_status":"active",
        "source_role":"authority","authority_class":"licensed_translation","text_mode":"vision_required"}
    if not isinstance(catalog,dict) or any(catalog.get(k)!=v for k,v in expected.items()):
        raise ValueError("original_source_mismatch")
    if existing_id or same_named_monster:
        raise ValueError("monster_collision")
    if name in EXISTING_CROSS_SOURCE_NAMES:
        raise ValueError("existing_phb_monster_requires_full_comparison")
    if name not in SEALED:
        raise ValueError("not_a_statblock")
    d=MONSTERS[name]
    current=(d["page"],d["type"],d["size"],d["align"],d["ac"],d["hp"],
        d["speed"],d["gs"],tuple(d["scores"]),tuple(d["traits"]),tuple(d["actions"]))
    if current!=SEALED[name] or d["page"] not in range(317,325):
        raise ValueError("source_fields_changed")
    match=HP_RE.fullmatch(d["hp"])
    if not match:
        raise ValueError("invalid_hit_dice")
    avg,count,sides,sign,modifier=match.groups()
    bonus=int(modifier or 0)*(-1 if sign=="-" else 1)
    if int(avg)!=int(count)*(int(sides)+1)//2+bonus:
        raise ValueError("hit_dice_mean_inconsistent")
    if len(d["scores"])!=6 or any(type(v) is not int or not 1<=v<=30 for v in d["scores"]):
        raise ValueError("invalid_six_scores")
    attrs={
      "classe_armatura":d["ac"],"punti_ferita":d["hp"],"velocita":d["speed"],"grado_sfida":d["gs"],
      "caratteristiche":dict(zip(("for","des","cos","int","sag","car"),(str(x) for x in d["scores"]))),
      "tipo_creatura":d["type"],"taglia":d["size"],"sottotipo_creatura":"",
      "allineamento":d["align"],"tratti_nomi_da_completare":list(d["traits"]),
      "azioni_nomi_da_completare":list(d["actions"]),"azioni_leggendarie_nomi_da_completare":[],
      "completezza_scheda":"statistiche_essenziali"}
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("global_semantic_numeric_gate")
    excerpt=(f"{name}. {d['type']} {d['size']}, {d['align']}. Classe Armatura {d['ac']}. "
             f"Punti Ferita {d['hp']}. Velocità {d['speed']}. Sfida {d['gs']}.")
    identity=f"{SOURCE_ID}|{FILENAME}|{d['page']}|{name.casefold()}"
    return {"id":"ref_"+hashlib.sha256(identity.encode()).hexdigest()[:32],
      "name":name,"physical_page":d["page"],"attributes":deepcopy(attrs),
      "source_excerpt":excerpt,"source_text_checksum":hashlib.sha256(excerpt.encode()).hexdigest(),
      "status":"source_checked_essential_statistics_only","writes":0}
