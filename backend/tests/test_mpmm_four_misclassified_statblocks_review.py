"""No-write registered-source guards for four distinct Italian MPMM monsters."""
import hashlib
from copy import deepcopy
import pytest
import services.mpmm_four_misclassified_statblocks_review as check
from services.mpmm_four_misclassified_statblocks_review import TARGETS,OWNER,SOURCE,authority,review_named_statblock
from services.ocr_semantic_gates import monster_semantic_numeric_flags

FAKE="Synthetic raw source for unit test; no original copyrighted prose. "*5


@pytest.fixture(params=list(TARGETS))
def original(request,monkeypatch):
    name=request.param
    s=TARGETS[name]
    clone=deepcopy(TARGETS)
    clone[name]["sha"]=hashlib.sha256(FAKE.encode()).hexdigest()
    monkeypatch.setattr(check,"TARGETS",clone)
    return name,{
        "id":s["id"],"user_id":OWNER,"name":name,"source_name":name,
        "normalized_name":name.casefold(),"reference_type":s["type"],
        "review_status":"needs_review","review_flags":s["flags"],
        "canonical_id":None,"source_key":SOURCE,"source_language":"it",
        "source_text_checksum":s["checksum"],"source_refs":[authority(s["page"])],
        "attributes":{},"source_attributes":{},
        "review_corrections":deepcopy(s["corrections"]),
        "full_text":FAKE,"source_full_text":FAKE,
    }


def test_exact_independent_source_is_eligible_readonly(original):
    name,row=original
    before=deepcopy(row)
    verdict=review_named_statblock(name,row)
    assert verdict["status"]=="eligible_original_boxed_monster_reclassification"
    assert verdict["writes"]==0
    assert verdict["correct_attributes"]==TARGETS[name]["attrs"]
    assert row==before
    assert not monster_semantic_numeric_flags(verdict["correct_attributes"])


@pytest.mark.parametrize(("field","invalid"),[
    ("id","other"),("user_id","wrong"),("name","wrong"),
    ("source_name","wrong"),("normalized_name","wrong"),
    ("reference_type","monster"),("review_status","verified"),
    ("review_flags",["ocr_da_verificare"]),("canonical_id","duplicate"),
    ("source_key","wrong.pdf"),("source_language","en"),
    ("source_text_checksum","0"*64),("source_refs",[]),
    ("attributes",{"punti_ferita":"68"}),("source_attributes",{"punti_ferita":"68"}),
    ("review_corrections",{"other":True}),
    ("full_text","tampered"),("source_full_text","tampered"),
])
def test_any_source_drift_blocks(original,field,invalid):
    name,row=original
    row[field]=invalid
    with pytest.raises(ValueError):
        review_named_statblock(name,row)


@pytest.mark.parametrize(("field","invalid"),[
    ("page",90),("logical_page",190),("filename","another.pdf"),
    ("source_role","secondary"),("source_status","inactive"),
    ("authority_class","unlicensed"),("logical_source_id","wrong"),
    ("ruleset","2024"),
])
def test_wrong_independent_statblock_page_rejected(original,field,invalid):
    name,row=original
    row["source_refs"][0][field]=invalid
    with pytest.raises(ValueError):
        review_named_statblock(name,row)


def test_extra_refs_or_wrong_monster_rejected(original):
    name,row=original
    row["source_refs"].append(deepcopy(row["source_refs"][0]))
    with pytest.raises(ValueError):
        review_named_statblock(name,row)
    with pytest.raises(ValueError):
        review_named_statblock("Not The Registered Monster",row)


def test_original_HP_dice_and_math_gates():
    for s in TARGETS.values():
        hp,count,faces,bonus=s["dice"]
        assert (count*(faces+1))//2+bonus==hp
        invalid=dict(s["attrs"])
        invalid["punti_ferita"]=f"{hp} ({count}d{faces} + {bonus+1})"
        assert monster_semantic_numeric_flags(invalid)
