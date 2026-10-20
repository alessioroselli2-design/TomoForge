"""Carognetta source review regression tests for OCR column spill."""
import pytest

from scripts.vrgr_apprendista_source_review import hit_dice_coherent
from scripts.vrgr_carognetta_source_review import (
    BAD_OCR_HP, CAROGNETTA_CORE, SOURCE_SHA256, validate_review,
)


def test_malformed_ocr_column_spill_is_rejected():
    assert not hit_dice_coherent(BAD_OCR_HP)
    assert hit_dice_coherent(CAROGNETTA_CORE["punti_ferita"])
    assert CAROGNETTA_CORE["punti_ferita"] == "27 (6d6 + 6)"


def test_physical_page_and_core_values_match_source_visual():
    assert CAROGNETTA_CORE["physical_page"] == 228
    assert CAROGNETTA_CORE["classe_armatura"] == "15 (armatura naturale)"
    assert CAROGNETTA_CORE["velocita"] == "7,5 m"
    assert CAROGNETTA_CORE["caratteristiche"] == {
        "for": "10", "des": "15", "cos": "12", "int": "8", "sag": "14", "car": "14"
    }
    assert CAROGNETTA_CORE["grado_sfida"] == "1"
    assert CAROGNETTA_CORE["completezza_scheda"] == "statistiche_essenziali"


def test_authority_and_collision_fail_closed():
    validate_review(CAROGNETTA_CORE, SOURCE_SHA256, ["Apprendista", "Mago Apprendista"])
    with pytest.raises(ValueError, match="source_sha256_mismatch"):
        validate_review(CAROGNETTA_CORE, "wrong", [])
    with pytest.raises(ValueError, match="duplicate_carognetta"):
        validate_review(CAROGNETTA_CORE, SOURCE_SHA256, ["carognetta"])


def test_ocr_never_directly_replaces_visual_review():
    incorrect = {**CAROGNETTA_CORE, "punti_ferita": BAD_OCR_HP}
    with pytest.raises(ValueError, match="reviewed_core_changed"):
        validate_review(incorrect, SOURCE_SHA256, [])
