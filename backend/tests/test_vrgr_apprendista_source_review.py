"""Regression: visual source resolution of OCR-mangled Apprendista HP."""
import pytest

from scripts.vrgr_apprendista_source_review import (
    APPRENDISTA_CORE,
    BAD_OCR_HP,
    SOURCE_SHA256,
    hit_dice_coherent,
    validate_review,
)


def test_original_ocr_failure_is_not_accepted():
    assert not hit_dice_coherent(BAD_OCR_HP)
    assert hit_dice_coherent(APPRENDISTA_CORE["punti_ferita"])
    assert APPRENDISTA_CORE["punti_ferita"] == "7 (2d8 - 2)"


def test_abilities_and_challenge_rating_do_not_invent_numbers():
    assert APPRENDISTA_CORE["physical_page"] == 201
    assert APPRENDISTA_CORE["caratteristiche"] == {
        "for": "8", "des": "10", "cos": "9", "int": "13", "sag": "11", "car": "12"
    }
    assert APPRENDISTA_CORE["grado_sfida"] == "—"
    assert APPRENDISTA_CORE["completezza_scheda"] == "statistiche_essenziali"


def test_exact_duplication_blocks_but_distinct_mpmm_mage_is_not_fused():
    validate_review(APPRENDISTA_CORE, SOURCE_SHA256, ["Mago Apprendista"])
    with pytest.raises(ValueError, match="duplicate_exact_apprendista"):
        validate_review(APPRENDISTA_CORE, SOURCE_SHA256, ["Apprendista"])
    with pytest.raises(ValueError, match="source_hash_mismatch"):
        validate_review(APPRENDISTA_CORE, "bad_hash", [])


def test_no_automatic_ocr_override_or_unreviewed_changes():
    corrected = {**APPRENDISTA_CORE, "punti_ferita": BAD_OCR_HP}
    with pytest.raises(ValueError, match="reviewed_core_facts_changed"):
        validate_review(corrected, SOURCE_SHA256, [])
    altered = {**APPRENDISTA_CORE, "grado_sfida": "0"}
    with pytest.raises(ValueError, match="reviewed_core_facts_changed"):
        validate_review(altered, SOURCE_SHA256, [])
