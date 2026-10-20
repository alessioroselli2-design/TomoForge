"""Source/read-only gates MM p179–182, 3 Hobgoblin ranks, Idra, Ippogrifo."""
from copy import deepcopy
import pytest
from services import mm_hobgoblin_idra_ippogrifo_pages_179_182_review as mm

def catalog():
    return {
       "logical_source_id":mm.SOURCE_ID,"physical_filename":mm.FILENAME,
       "physical_sha256":mm.SHA256,"physical_pages":mm.PDF_PAGES,
       "source_status":"active","source_role":"authority",
       "authority_class":"licensed_translation","text_mode":"vision_required",
    }

@pytest.mark.parametrize(("name","page","hp","gs"),[["Hobgoblin",179,"11 (2d8 + 2)","1/2"],["Hobgoblin Capitano",179,"39 (6d8 + 12)","3"],["Hobgoblin Signore Della Guerra",180,"97 (13d8 + 39)","6"],["Idra",181,"172 (15d12 + 75)","8"],["Ippogrifo",182,"19 (3d10 + 3)","1"]])
def test_all_original_boxes(name,page,hp,gs):
    r=mm.audit(name,catalog())
    assert r["physical_page"]==page
    assert r["attributes"]["punti_ferita"]==hp
    assert r["attributes"]["grado_sfida"]==gs
    assert r["writes"]==0

def test_hobgoblin_ordinary_and_capitano_are_independent_p179():
    a=mm.audit("Hobgoblin",catalog())
    b=mm.audit("Hobgoblin Capitano",catalog())
    assert a["id"]!=b["id"] and a["physical_page"]==b["physical_page"]==179

def test_idra_has_all_trait_names_without_claiming_full_actions():
    r=mm.audit("Idra",catalog())
    assert r["attributes"]["tratti_nomi_da_completare"]==[
        "Trattenere il Respiro","Teste Multiple","Teste Reattive","Sempre Sveglio",
    ]
    assert r["attributes"]["completezza_scheda"]=="statistiche_essenziali"

@pytest.mark.parametrize("name",list(mm.MONSTERS))
def test_collision_rejected(name):
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),existing_id=True)
    with pytest.raises(ValueError,match="duplicate"):
        mm.audit(name,catalog(),duplicate_monsters=[{"name":name}])

def test_source_sha_changed_fails_closed():
    c=catalog();c["physical_sha256"]="0"*64
    with pytest.raises(ValueError,match="authority_mismatch"):
        mm.audit("Ippogrifo",c)

@pytest.mark.parametrize(("name","field","wrong"),[
    ("Hobgoblin","hp","12 (2d8 + 3)"),
    ("Hobgoblin Capitano","scores",[15,14,15,12,10,13]),
    ("Hobgoblin Signore Della Guerra","gs","7"),
    ("Idra","traits",["Teste Multiple"]),
    ("Ippogrifo","speed","9 m"),
])
def test_changed_source_not_accepted(name,field,wrong,monkeypatch):
    changed=deepcopy(mm.MONSTERS);changed[name][field]=wrong
    monkeypatch.setattr(mm,"MONSTERS",changed)
    with pytest.raises(ValueError,match="sealed_original"):
        mm.audit(name,catalog())
