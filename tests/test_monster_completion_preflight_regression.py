"""Regression checks for missing localized text and immutable monster identity."""
from monster_completion_preflight import preflight


def _record_pair():
    original = {
        "id": "ref_test", "user_id": "owner", "reference_type": "monster",
        "source_refs": [{"page": 1}], "review_status": "verified",
        "source_name": "Example", "source_description": "",
        "source_full_text": "", "source_attributes": {}, "source_language": "en",
        "translation_status": "processing", "translation_lease_id": "",
        "translation_lease_expires_at": 0,
    }
    candidate = {
        **original, "name": "Esempio", "description": "Descrizione completa.",
        "full_text": "Testo completo.", "translation_status": "translated",
        "translation_review_status": "pending",
        "attributes": {
            "tipo": "Mostruosità", "taglia": "Media", "allineamento": "neutrale",
            "classe_armatura": "15", "punti_ferita": "25", "velocita": "9 m",
            "caratteristiche": {"for": 10, "des": 10, "cos": 10,
                                 "int": 10, "sag": 10, "car": 10},
            "sensi": "Percezione passiva 10", "linguaggi": "Nessuno",
            "grado_sfida": "1", "tratti": [], "azioni": [],
            "reazioni": [], "azioni_leggendarie": [],
        },
    }
    return original, candidate


def _check(original, candidate):
    return preflight(original, candidate, source_page_checked=True,
                     source_sections_checked=True, independent_review=True)


def test_complete_record_can_pass_structural_preflight():
    original, candidate = _record_pair()
    assert _check(original, candidate).ready


def test_blank_full_text_is_rejected():
    original, candidate = _record_pair()
    candidate["full_text"] = "  "
    result = _check(original, candidate)
    assert not result.ready
    assert "full_text_missing" in result.blockers


def test_changed_owner_is_rejected():
    original, candidate = _record_pair()
    candidate["user_id"] = "other"
    result = _check(original, candidate)
    assert not result.ready
    assert "immutable_identity_changed:user_id" in result.blockers


def test_changed_reference_type_is_rejected():
    original, candidate = _record_pair()
    candidate["reference_type"] = "spell"
    result = _check(original, candidate)
    assert not result.ready
    assert "immutable_identity_changed:reference_type" in result.blockers
