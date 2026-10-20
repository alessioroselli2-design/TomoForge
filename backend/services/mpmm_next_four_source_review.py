"""Read-only original Italian MPMM audit for four more misclassified encounters."""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

SRC = "Mostri del multiverso 101-200.pdf"
OWNER = "user_fabf28726a20"
TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
TARGETS = {
    "Duergar Signore Della Guerra": {
        "id":"ref_310d139d5e9d515f917bd38fc228d926",
        "page":14,"logical_page":114,
        "checksum":"7c91b7aee61ac9b2e7676e9c6c44c1b95035a5cc729636eee2a766c58431c4f6",
        "raw_sha256":"adc0dd7420b0299e7adcc38fc4ccca10441e9054685b89911e9d5ee7c62d8e7a",
        "attrs":{"classe_armatura":"20 (armatura a piastre, scudo)",
                 "punti_ferita":"75 (10d8 + 30)","velocita":"7,5 m"},
        "dice":(75,10,8,30),
    },
    "Fiore Cadavere": {
        "id":"ref_e628346d79c05bb28c12d91943167c61",
        "page":24,"logical_page":124,
        "checksum":"a7b5e56bb6253b45690eab041b3a188fd3c685eba39bbdcd43b1eb11db09f4c0",
        "raw_sha256":"12b8339c943aea391cc0a7d9f076cb60226a0de3da922588bade41869e5cff18",
        "attrs":{"classe_armatura":"12","punti_ferita":"127 (15d10 + 45)","velocita":"6 m, scalare 6 m"},
        "dice":(127,15,10,45),
    },
    "Gauth": {
        "id":"ref_24c04aed06b450e8a2adefb7e01eb814",
        "page":28,"logical_page":128,
        "checksum":"e026c3a6bdd3972e5019fd140b6dc92e518b074c09827a8a4d839cae94926b3f",
        "raw_sha256":"673c094d9c725255782c75d80c79942f7709ec3d1be43a5a7fb41db8308da8fe",
        "attrs":{"classe_armatura":"15 (armatura naturale)","punti_ferita":"52 (7d8 + 21)","velocita":"0 m, volare 6 m (fluttuare)"},
        "dice":(52,7,8,21),
    },
    "Girallon": {
        "id":"ref_2f296a7e2d395b7e8618ed3b5b82ae2e",
        "page":34,"logical_page":134,
        "checksum":"6342450dcc75f5d97c4a0596be584aa23032abfd6f69f31b7f6e8c9918616022",
        "raw_sha256":"1c5a40d134b227a44361027330d2df3bad811cd154fc4d654603308f4d22f14e",
        "attrs":{"classe_armatura":"13","punti_ferita":"59 (7d10 + 21)","velocita":"12 m, scalare 12 m"},
        "dice":(59,7,10,21),
    },
}


def authority(page: int, logical_page: int) -> dict[str, Any]:
    return {
        "page":page,"ruleset":"2014","filename":SRC,"source_role":"authority",
        "logical_page":logical_page,"source_title":TITLE,
        "source_status":"active","authority_class":"licensed_translation",
        "logical_source_id":"mpmm_2022_it",
    }


def audit_mpmm_encounter(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    if name not in TARGETS or not isinstance(row,dict):
        raise ValueError("source_candidate_missing")
    t=TARGETS[name]
    original={
       "id":t["id"],"user_id":OWNER,"name":name,"source_name":name,
       "normalized_name":name.casefold(),"reference_type":"other",
       "review_status":"needs_review","review_flags":[],
       "source_language":"it","source_key":SRC,"canonical_id":None,
       "source_text_checksum":t["checksum"],"attributes":{},"source_attributes":{},
       "review_corrections":{"_source_changed":True},
       "source_refs":[authority(t["page"],t["logical_page"])],
    }
    if any(row.get(k)!=v for k,v in original.items()):
        raise ValueError("registered_original_source_snapshot_changed")
    raw=row.get("source_full_text")
    if not isinstance(raw,str) or row.get("full_text")!=raw:
        raise ValueError("raw_source_description_modified")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest()!=t["raw_sha256"]:
        raise ValueError("original_registered_sha256_changed")
    hp,dice,faces,bonus=t["dice"]
    if (dice*(faces+1))//2+bonus!=hp:
        raise ValueError("source_statblock_dice_average_wrong")
    if monster_semantic_numeric_flags(t["attrs"]):
        raise ValueError("unmodified_global_numeric_gate_failed")
    return {
      "name":name,"id":t["id"],"logical_page":t["logical_page"],
      "status":"eligible_original_source_reclassification",
      "attributes":t["attrs"],"original_raw_unchanged":True,"writes":0,
    }
