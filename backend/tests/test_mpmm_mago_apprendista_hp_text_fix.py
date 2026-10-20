"""Mago Apprendista MPMM OCR traceability and fail-closed regression."""
from copy import deepcopy

import pytest

from services import mpmm_mago_apprendista_hp_text_fix as f


def original():
    return {
        "id": f.RECORD_ID,
        "name": f.NAME,
        "source_key": f.SOURCE_KEY,
        "review_status": "verified",
        "source_text_checksum": f.SOURCE_CHECKSUM,
        "source_refs": [
            {"logical_source_id": "mpmm_2022_it", "logical_page": 168},
            {"logical_source_id": "mpmm_2022_it", "logical_page": 169},
        ],
        "source_attributes": {"punti_ferita": "1"},
        "attributes": {
            "punti_ferita": "13 (3d8)",
            "classe_armatura": "10 (13 con armatura magica)",
            "velocita": "9 m",
        },
        "source_full_text": "Umanoide Medio, Punti Ferita 1 3 (3d8) Velocità 9 m",
        "full_text": "Umanoide Medio, Punti Ferita 1 3 (3d8) Velocità 9 m",
        "description": "Umanoide Medio, Punti Ferita 1 3 (3d8) Velocità 9 m",
    }


def test_only_corrects_canonical_prose_and_preserves_raw_ocr():
    record = original()
    snapshot = deepcopy(record)
    result = f.prepare_correction(record)
    assert result["full_text"] == "Umanoide Medio, Punti Ferita 13 (3d8) Velocità 9 m"
    assert result["description"] == result["full_text"]
    assert result["preserve"]["source_full_text"] == snapshot["source_full_text"]
    assert result["preserve"]["source_attributes"]["punti_ferita"] == "1"
    assert result["preserve"]["attributes"]["punti_ferita"] == "13 (3d8)"
    assert record == snapshot
    assert result["writes"] == 0


@pytest.mark.parametrize("field,replacement,expected", [
    ("id", "other", "record_identity_mismatch"),
    ("review_status", "pending", "review_status_changed"),
    ("source_key", "other.pdf", "registered_source_mismatch"),
    ("source_text_checksum", "bad", "source_evidence_checksum_mismatch"),
    ("source_refs", [], "original_pages_mismatch"),
    ("source_full_text", "Punti Ferita 13 (3d8)", "original_ocr_evidence_mismatch"),
    ("full_text", "Punti Ferita 1 (3d8)", "canonical_text_drift"),
])
def test_source_and_snapshot_drift_fails_closed(field, replacement, expected):
    record = original()
    record[field] = replacement
    with pytest.raises(ValueError, match=expected):
        f.prepare_correction(record)


def test_no_automatic_canonicalization_or_source_rewrite():
    record = original()
    record["source_attributes"]["punti_ferita"] = "13 (3d8)"
    with pytest.raises(ValueError, match="hit_point_core_fields_mismatch"):
        f.prepare_correction(record)
    record = original()
    record["attributes"]["punti_ferita"] = "9 (2d8)"
    with pytest.raises(ValueError, match="hit_point_core_fields_mismatch"):
        f.prepare_correction(record)
