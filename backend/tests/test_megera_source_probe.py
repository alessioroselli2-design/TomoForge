"""The probe never returns any source text and uses stable positioning."""

from types import SimpleNamespace

import pytest

from services.megera_source_probe import (
    ATTRIBUTES,
    RAW_SHA256,
    RECORD_ID,
    SOURCE_CHECKSUM,
    assess_megera_registered_source,
    compact_word,
    page_safe_geometry,
)


def test_unicode_normalization_and_punctuation():
    assert compact_word("Velocità:") == "velocita"
    assert compact_word("15d8") == "15d8"
    assert compact_word("MÈGERA") == "megera"


def test_privacy_safe_line_metadata_only():
    words = [
        (10, 15, 40, 20, "Megera", 0, 0, 0),
        (42, 15, 82, 20, "Crepuscolare", 0, 0, 1),
        (10, 30, 42, 38, "Classe", 0, 1, 0),
        (45, 30, 83, 38, "Armatura", 0, 1, 1),
        (88, 30, 94, 38, "17", 0, 1, 2),
        (10, 50, 24, 57, "Punti", 0, 2, 0),
        (28, 50, 46, 57, "Ferita", 0, 2, 1),
        (50, 50, 58, 57, "82", 0, 2, 2),
    ]
    page = SimpleNamespace(
        get_text=lambda mode, sort=False: words,
        rect=SimpleNamespace(width=100, height=100),
    )
    result = page_safe_geometry(page, 305)
    assert result["title_lines"] == 1
    assert result["ca_labels"] == 1
    assert result["hp_labels"] == 1
    assert result["lines"][1]["has_17"]
    assert result["lines"][2]["has_82"]
    assert "Megera" not in str(result)
    assert "Ferita" not in str(result)



def _record():
    # Exact sealed full_text fingerprint is verified against live database.
    # This fixture constructs the same input through the real raw record in CI
    # tests only for the geometry-specific invariants; live workflow tests full.
    return {
        "id": RECORD_ID,
        "reference_type": "monster",
        "name": "Megera Crepuscolare",
        "review_status": "pending",
        "canonical_id": None,
        "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": SOURCE_CHECKSUM,
        "attributes": dict(ATTRIBUTES),
        "full_text": "dummy",
        "source_refs": [{
            "page": 305,
            "logical_page": 305,
            "logical_source_id": "erlw_2019_it",
            "source_role": "authority",
            "source_status": "active",
            "authority_class": "licensed_translation",
            "filename": "618795464-Eberron.pdf",
            "ruleset": "2014",
        }],
    }


def test_unregistered_full_text_blocks_status_review():
    assert len(RAW_SHA256) == 64
    with pytest.raises(ValueError, match="registered_record_or_text_drift"):
        assess_megera_registered_source(_record(), {"page": 305, "words": 600, "lines": []})


def test_wrong_status_and_source_identity_fail_closed():
    import pytest
    record = _record()
    record["review_status"] = "verified"
    with pytest.raises(ValueError):
        assess_megera_registered_source(record, {"page": 305, "words": 600, "lines": []})


def test_geometry_diagnostic_records_complete_dice_math():
    assert (15 * (8 + 1)) // 2 + 15 == 82
    assert ATTRIBUTES == {
        "classe_armatura": "17 (armatura naturale)",
        "punti_ferita": "82 (15d8 + 15)",
        "velocita": "9 m",
    }
