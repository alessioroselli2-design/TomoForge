"""Bounded, read-only Van Richten OCR candidate extraction."""
from scripts import vrgr_r2_candidate_dry_run as d


def test_candidate_exports_only_factual_fields():
    record = {
        "name": "Mostro da verificare",
        "start_page": 205,
        "review_flags": ["ocr_independent_agreement", "ocr_da_verificare"],
        "attributes": {
            "classe_armatura": "15", "punti_ferita": "27 (5d8 + 5)",
            "velocita": "9 m", "description": "PRIVATE DESCRIPTION SHOULD NOT LEAK",
        },
        "full_text": "PRIVATE ORIGINAL OCR SHOULD NOT LEAK",
    }
    item = d.metadata_candidate(record)
    assert item["manual_review_required"]
    assert item["physical_page"] == 205
    assert set(item) == {
        "name", "physical_page", "core_fields",
        "independent_ocr_agreement", "manual_review_required",
    }
    assert "PRIVATE" not in str(item)
    assert d.WRITES == 0


def test_reject_nonindependent_or_missing_numeric():
    record = {
        "name": "Nome", "start_page": 205,
        "review_flags": ["ocr_da_verificare"],
        "attributes": {"classe_armatura": "15", "punti_ferita": "9 (2d8)", "velocita": "9 m"},
    }
    assert d.metadata_candidate(record) is None
    record["review_flags"].append("ocr_independent_agreement")
    del record["attributes"]["velocita"]
    assert d.metadata_candidate(record) is None
    record["attributes"]["velocita"] = "9 m"
    record["start_page"] = 999
    assert d.metadata_candidate(record) is None


def test_invalid_hit_dice_is_blocked():
    assert d.hit_dice_coherent("27 (5d8 + 5)") is True
    assert d.hit_dice_coherent("7 (248 - 2)") is False
    assert d.hit_dice_coherent("9 (2d8)") is True
    assert d.hit_dice_coherent("10 (2d8)") is False
    src = {
        "name": "Apprendista",
        "start_page": 201,
        "review_flags": ["ocr_independent_agreement"],
        "attributes": {
            "classe_armatura": "10",
            "punti_ferita": "7 (248 - 2)",
            "velocita": "9 m",
        },
    }
    assert d.metadata_candidate(src) is None


def test_numeric_only_diagnostic_does_not_leak_source_prose():
    signature = d.numeric_hp_tokens("7 (248 - 2) PRIVATE TEXT copyright")
    assert signature == "7 ( 248 - 2 )"
    assert "PRIVATE" not in signature and "copyright" not in signature
    assert d.numeric_hp_tokens("7 (2d8 - 2)") == "7 ( 2 d 8 - 2 )"
    assert d.hit_dice_coherent("7 (248 - 2)") is False
